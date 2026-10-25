import asyncio
import os
import logging 
from dotenv import load_dotenv
from agents import set_tracing_disabled
from agents.mcp import MCPServerStreamableHttp

load_dotenv()
set_tracing_disabled(True)

# Keep logs clean but show important MCP connection status
logging.basicConfig(level=logging.INFO)
logging.getLogger("mcp").setLevel(logging.WARNING)

async def main():
    sonicaura_key = os.getenv("SONICAURA_API_KEY")
    if not sonicaura_key:
        print("❌ Error: SONICAURA_API_KEY not found in .env file. Please check your configuration.")
        return

    print("🔌 Connecting to SonicAura Remote MCP Server...")
    
    try:
        async with MCPServerStreamableHttp(
            name="SonicAura",
            params={
                "url": "https://api.sonicaurastudio.com/mcp",
                "headers": {"Authorization": f"Bearer {sonicaura_key}"}
            }
        ) as sonicaura_server:

            # === ONLY FETCH AND PRINT TOOLS ===
            try:
                tools = await sonicaura_server.list_tools()
                print(f"\n✅ Connected! Available tools ({len(tools)}):")
                for t in tools:
                    print(f"  - {t.name}: {t.description}")
                print("-" * 60)
                print("\n💡 Notice: Audio processing (GPU execution) is currently locked for public demos.")
                print("👉 To enable full processing, please apply for an API quota or modify the script to include the Runner logic.")
                
            except Exception as e:
                print(f"❌ Failed to fetch tools! The server might be down or the API Key is invalid. Error: {e}")
                return

            # =====================================================================
            # 🚨 NOTICE: Processing logic (Upload + Agent Execution) is disabled.
            # To re-enable it in the future, refer to the previous version of main.py.
            # =====================================================================
            
         

    except Exception as e:
        print(f"❌ Critical connection failure to SonicAura MCP Server: {e}")

if __name__ == "__main__":
    asyncio.run(main())