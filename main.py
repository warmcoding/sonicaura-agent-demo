import asyncio
import os
import json
import requests
import logging 
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, Runner, set_tracing_disabled
from agents.mcp import MCPServerStreamableHttp
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

load_dotenv()
set_tracing_disabled(True)

# Keep this to see raw HTTP requests if errors occur, but suppress harmless SDK warnings
logging.basicConfig(level=logging.INFO)
logging.getLogger("mcp").setLevel(logging.WARNING)
logging.getLogger("openai.agents").setLevel(logging.ERROR) 

async def main():
    # 1. Initialize LLM Client
    deepseek_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.deepseek.com/v1"
    )
    deepseek_model = OpenAIChatCompletionsModel(
        model="deepseek-chat",
        openai_client=deepseek_client
    )

    sonicaura_key = os.getenv("SONICAURA_API_KEY")
    if not sonicaura_key:
        print("❌ Error: SONICAURA_API_KEY not found in .env file. Please check your configuration.")
        return

    print("🔌 Connecting to SonicAura Remote MCP Server...")
    print("💡 Note: If this is your first request in a while, Modal may take 5-10 seconds to cold start.")

  
    max_retries = 3

    for attempt in range(max_retries):
        try:
            async with MCPServerStreamableHttp(
                name="SonicAura",
                params={
                    "url": "https://api.sonicaurastudio.com/mcp",
                    "headers": {"Authorization": f"Bearer {sonicaura_key}"}
                }
            ) as sonicaura_server:

                # === 1. Fetch and print the actual tools list from the server ===
                try:
                    tools = await sonicaura_server.list_tools()
                    print(f"\n✅ Connected! Available tools ({len(tools)}):")
                    for t in tools:
                        print(f"  - {t.name}")
                    print("-" * 60)
                except Exception as e:
                    raise Exception(f"Failed to fetch tools: {e}")

                # === 2. Initialize the Agent ===
                podcast_agent = Agent(
                    name="Audio Preprocessor",
                    model=deepseek_model,
                    instructions=(
                        "You are an expert audio assistant. "
                        "When you use a processing tool, it returns a `task_id`. "
                        "You MUST immediately call `check_task_status` with that `task_id` to poll for completion. "
                        "If the status is 'processing', call `check_task_status` again. "
                        "Once the status is 'done', look inside the `tracks` dictionary in the response to find the download URLs, and return them to the user."
                    ),
                    mcp_servers=[sonicaura_server]
                )

                test_audio_path = os.path.abspath("./samples/noisy_audio.mp3") 
                if not os.path.exists(test_audio_path):
                    print(f"⚠️ Test file not found: {test_audio_path}")
                    return

                # === 3. Request a presigned upload URL ===
                print("\n[Step 1] Requesting upload URL from SonicAura...")
                try:
                    url_result = await sonicaura_server.call_tool(
                        "get_upload_url", 
                        arguments={"filename": "noisy_audio.mp3"}
                    )
                    raw_text = url_result.content[0].text
                    parsed_result = json.loads(raw_text)
                    upload_url = parsed_result.get("upload_url")
                    file_key = parsed_result.get("source_key")
                    
                    if not upload_url or not file_key:
                        print(f"❌ Failed to parse response: {raw_text}")
                        return
                        
                    print(f"✅ Got upload URL! Source Key: {file_key}")
                except Exception as e:
                    print(f"❌ Failed to get upload URL! Error: {e}")
                    return

                # === 4. Python handles direct upload ===
                print("[Step 2] Direct uploading file to cloud storage...")
                headers = {"Content-Type": "audio/mpeg"} 
                with open(test_audio_path, 'rb') as f:
                    res = requests.put(upload_url, data=f, headers=headers)
                    
                if res.status_code in [200, 201, 204]:
                    print("✅ Upload successful!")
                else:
                    print(f"❌ Upload failed, status code: {res.status_code}")
                    return

                # === 5. Hand over to Agent for async polling ===
                print("\n[Step 3] 🤖 Starting Agent workflow...")
                
                prompt = f"""
                The audio file has been successfully uploaded. 
                The source_key is: '{file_key}'
                
                Please extract the vocals (2 stems) from this audio file.
                Poll the status until it is done.
                
                IMPORTANT: This is a 2-stem extraction. You MUST return BOTH the 'vocals' and 'no_vocals' download URLs. 
                If the status is 'done' but 'no_vocals' is missing, it means the file is still uploading. Please wait and call `check_task_status` again until both are present in the `tracks` dictionary.
                """
                
                try:
                    result = await Runner.run(podcast_agent, prompt, max_turns=30)
                    print("\n" + "="*50)
                    print("✅ Processing Complete! Agent Final Output:")
                    print(result.final_output)
                    print("="*50)
                except Exception as e:
                    print(f"❌ Agent execution failed: {e}")
                
               
                return 

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"\n⚠️ Connection failed (Attempt {attempt + 1}/{max_retries}): {e}")
                print("⏳ Retrying in 3 seconds (Waiting for server to wake up)...")
                await asyncio.sleep(3)
            else:
                print(f"\n❌ Critical connection failure after {max_retries} attempts: {e}")

if __name__ == "__main__":
    asyncio.run(main())