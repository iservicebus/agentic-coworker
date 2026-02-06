from agents.utils.llm import LLM

# Load environment variables from .env file in the parent directory
# Place this near the top, before using env vars like API keys
import os

from langgraph.checkpoint.memory import InMemorySaver

from rich.console import Console
from rich.markdown import Markdown

console = Console()

import requests
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from typing import Optional


# Keycloak configuration
AUTH_URL = "http://localhost:8888"


TENANT = "default"
AGENT_ID = "agent-dev"
AGENT_SECRET = "securepass"

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from typing import Optional
from langchain_mcp_adapters.tools import load_mcp_tools


TOKEN_URL = f"{AUTH_URL}/realms/{TENANT}/protocol/openid-connect/token"

def get_access_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": AGENT_ID,
        "client_secret": AGENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=data)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        print("Access token:")
        print(access_token)
        return access_token
    else:
        print("Failed to get token")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        return None

def get_auth_headers():
    access_token = get_access_token()
    print("Access token acquired.")

    # === Step 2: Send API request with token and client ID ===
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Agent-ID": AGENT_ID
    }
    return headers


async def get_tools():
    server_url = "http://0.0.0.0:6666/sse"
    _streams_context = None
    _session_context = None
    session: Optional[ClientSession] = None

    try:
        # Create SSE client connection
        _streams_context = sse_client(url=server_url, headers=get_auth_headers())
        streams = await _streams_context.__aenter__()

        # Create MCP session using streams
        _session_context = ClientSession(*streams)
        session = await _session_context.__aenter__()

        await session.initialize()
        # Get tools
        tools = await load_mcp_tools(session)
 
        # List available tools to verify connection
        print("Initialized SSE client...")
        return tools

    except asyncio.CancelledError:
        print("Main task was cancelled. Shutting down cleanly...")
        raise
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
    finally:
        # Ensure proper cleanup
        if session and _session_context:
            await _session_context.__aexit__(None, None, None)
        if _streams_context:
            await _streams_context.__aexit__(None, None, None)



os.environ["OPENAI_API_VERSION"] = "2025-03-01-preview"

model=LLM().get_model()



async def main():

    server_url = "http://0.0.0.0:6666/sse"
    _streams_context = None
    _session_context = None
    session: Optional[ClientSession] = None

    try:
        # Create SSE client connection
        _streams_context = sse_client(url=server_url, headers=get_auth_headers())
        streams = await _streams_context.__aenter__()

        # Create MCP session using streams
        _session_context = ClientSession(*streams)
        session = await _session_context.__aenter__()

        await session.initialize()
        # Get tools
        tools = await load_mcp_tools(session)
 
        # List available tools to verify connection
        print("Initialized SSE client...")

    except asyncio.CancelledError:
        print("Main task was cancelled. Shutting down cleanly...")
        raise
    except Exception as e:
        print(f"Unexpected error occurred: {e}")


    from agents.base.base_agent import BaseAgent
    memory = InMemorySaver()
    agent= await BaseAgent(model, tools).build(checkpointer=memory)
    #agent= await BaseAgent(model, tools).build()



    from agents.utils.cli import format_messages
    from langchain_core.messages import HumanMessage

    from rich.console import Console
    from rich.markdown import Markdown
    console = Console()

    config = {"configurable": {"thread_id": "2"}}

    while True:
        try:

            user_input = str(input("User: "))
            if user_input.lower() in ["done",  "q"]:
                break
            result = await agent.ainvoke({"messages": [{"role": "user", "content": user_input}]}, config)
            format_messages(result['messages'])
        except Exception  as e:
            print(e)
            break





    # rs= await agent.ainvoke(
    #     {"messages": [{"role": "user", "content": "please get github repository for user jingnanzhou"}]}
    # )

    # print(rs)











if __name__ == "__main__":

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user (Ctrl+C)")
    except asyncio.CancelledError:
        print("CancelledError raised after asyncio.run shutdown")
    except Exception as e:
        print(f"Unhandled exception during shutdown: {e}")
