# SonicAura MCP x OpenAI Agents SDK Demo 🤖🎵

This repository demonstrates how to build an AI Agent that can **denoise, extract vocals, and apply studio effects** to large audio files using the [SonicAura MCP Server](https://www.sonicaurastudio.com/mcp/agent-development) and the **OpenAI Agents SDK**.

> **💡 Why this repo is special:** 
> Most LLM demos fail when you give them a file larger than 1MB because of context limits and JSON truncation. This repo demonstrates the **Production-Ready Pattern**: 
> 1. Python handles the heavy lifting (direct upload to cloud).
> 2. The Agent only commands the workflow via `source_key`.
> 3. The Agent automatically polls the asynchronous task status until complete.

## ✨ Features

- **Native MCP Integration**: Connects to SonicAura's remote MCP server via Streamable HTTP.
- **Large File Support**: Bypasses LLM context limits by using presigned URLs for direct uploads.
- **Asynchronous Polling**: Agents can handle long-running tasks and poll for completion without timing out.
- **Framework Agnostic**: Uses OpenAI Agents SDK, but works with DeepSeek, GPT-4o, or Claude.

## 🚀 Quickstart (2 Minutes)

### 1. Prerequisites
- **Python 3.10+**
- An **LLM API Key** (OpenAI, or a compatible provider like DeepSeek)
- A **SonicAura API Key** (Get 2 free executions per month at [SonicAura Studio](https://www.sonicaurastudio.com/auth/login))

### 2. Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/sonicaura-agent-demo.git
cd sonicaura-agent-demo

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt