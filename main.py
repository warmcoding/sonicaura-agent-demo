import asyncio
import os
import json
import requests
from dotenv import load_dotenv

from openai import AsyncOpenAI
from agents import Agent, Runner, set_tracing_disabled
from agents.mcp import MCPServerStreamableHttp
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

load_dotenv()
set_tracing_disabled(True)

async def main():
    # 1. Initialize LLM Client (Currently using DeepSeek, change base_url for OpenAI)
    deepseek_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.deepseek.com/v1"
    )
    deepseek_model = OpenAIChatCompletionsModel(
        model="deepseek-chat",
        openai_client=deepseek_client
    )

    sonicaura_key = os.getenv("SONICAURA_API_KEY")
    print("🔌 Connecting to SonicAura Remote MCP Server...")
    
    async with MCPServerStreamableHttp(
        name="SonicAura",
        params={
            "url": "https://api.sonicaurastudio.com/mcp",
            "headers": {"Authorization": f"Bearer {sonicaura_key}"}
        }
    ) as sonicaura_server:

        # 2. Initialize the Agent with clear instructions for async polling
        podcast_agent = Agent(
            name="Audio Preprocessor",
            model=deepseek_model,
            instructions=(
                "You are an expert audio assistant. "
                "The audio processing is asynchronous. "
                "When you call `process_audio` or `split_audio`, it will return a `task_id`. "
                "You MUST then call `check_task_status` with that `task_id`. "
                "If it returns 'processing', wait a moment and check again. Keep polling until it returns 'done'. "
                "Once done, return the final download URLs."
            ),
            mcp_servers=[sonicaura_server]
        )

        # Note: Make sure you have a test audio file in the 'samples' directory
        test_audio_path = os.path.abspath("./samples/noisy_audio.mp3") 
        
        if not os.path.exists(test_audio_path):
            print(f"⚠️ Test file not found: {test_audio_path}")
            return

        # ==========================================
        # Step 1: Request a presigned upload URL 
        # (Avoid passing large files directly to the LLM)
        # ==========================================
        print("Step 1: Requesting upload URL from SonicAura...")
        url_result = await sonicaura_server.call_tool(
            "get_upload_url", 
            arguments={"filename": "noisy_audio.mp3"}
        )
        raw_text = url_result.content[0].text
        parsed_result = json.loads(raw_text)
        upload_url = parsed_result.get("upload_url")
        file_key = parsed_result.get("source_key") # The backend returns 'source_key'
        
        if not upload_url or not file_key:
            print(f"❌ Failed to parse response: {raw_text}")
            return
            
        print(f"✅ Got upload URL! Source Key: {file_key}")

        # ==========================================
        # Step 2: Direct upload the file from Python
        # ==========================================
        print("Step 2: Direct uploading file to cloud storage...")
        headers = {"Content-Type": "audio/mpeg"} 
        
        with open(test_audio_path, 'rb') as f:
            res = requests.put(upload_url, data=f, headers=headers)
            
        if res.status_code in [200, 201, 204]:
            print("✅ Upload successful!")
        else:
            print(f"❌ Upload failed, status code: {res.status_code}")
            return

        # ==========================================
        # Step 3: Hand over to Agent for automated "Submit + Poll"
        # ==========================================
        print("\n🤖 Starting Agent workflow (it will submit the task and poll for results)...")
        
        # Note: If you refactored your MCP tools to `split_audio`, update the prompt accordingly.
        # We use '2stems' here as it runs on GPU and is the fastest.
        prompt = f"""
        The audio file has been successfully uploaded.
        Here is the source_key: '{file_key}'
        
        Please do the following:
        1. Use `process_audio` (or `split_audio` if available) with source_key='{file_key}' and task_type='2stems'.
        2. It will return a JSON with a `task_id`.
        3. Then, use `check_task_status` with that `task_id` and task_type='2stems'.
        4. If the status is 'processing', check again. Repeat up to 5 times until status is 'done'.
        5. Return the final URLs in your final answer.
        """
        
        # Increase max_turns to allow enough time for polling
        result = await Runner.run(podcast_agent, prompt, max_turns=10)

        print("\n" + "="*40)
        print("✅ Processing Complete! Agent Final Output:")
        print(result.final_output)
        print("="*40)

if __name__ == "__main__":
    asyncio.run(main())