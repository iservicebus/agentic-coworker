# ./adk_agent_samples/mcp_agent/agent.py
import asyncio
from dotenv import load_dotenv
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService # Optional
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset,  SseConnectionParams

import requests
import asyncio
from mcp.client.sse import sse_client
from dotenv import load_dotenv

from opik.integrations.adk import OpikTracer

load_dotenv()

opik_tracer = OpikTracer()



# Keycloak configuration
#AUTH_URL = "http://localhost:8888"
AUTH_URL = "http://host.docker.internal:8888"

TENANT = "default"
AGENT_ID="agent-dev"
AGENT_SECRET="securepass"
TENANT_NAME="default"

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
        "X-Agent-ID": AGENT_ID,
        "X-Tenant": TENANT
    }
    return headers

# Load environment variables from .env file in the parent directory
# Place this near the top, before using env vars like API keys

"""Initializes and returns the root agent with MCP tools."""
mcp_tool = MCPToolset(
    connection_params=SseConnectionParams(
        url="http://0.0.0.0:6666/sse", headers=get_auth_headers()
    )
)

from google.adk.models.lite_llm import LiteLlm

import os

#litellm=LiteLlm(model=llm_model)
system_agent_prompt =  """You are an assistant 
<Task>
Your job is to answer the user's input by calling provided tools. If the tool is not found, please use tool  search_tools_by_capability_tools_search_capability_post to search additional tools 
</Task>
"""

from google.adk.models.google_llm import Gemini

# --- Model Selection Toggle ---
# You can set this to "gemini" or "azure" in your .env file
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

def initialize_model():
    if LLM_PROVIDER == "gemini":
        print("Using Gemini 2.5 Flash...")
        return Gemini(
            model=os.getenv("GOOGLE_MODEL"),
            # Ensure GOOGLE_API_KEY is in your environment
        )
    
    elif LLM_PROVIDER == "azure":

        llm_model = os.getenv("VLLM_MODEL")

        print(f"Using Azure OpenAI ({llm_model})...")
        # For Azure, LiteLLM expects the "azure/" prefix
        
        return LiteLlm(
            model=llm_model,
            api_base=os.getenv("AZURE_API_BASE"),
            api_version=os.getenv("AZURE_API_VERSION"),
            api_key=os.getenv("AZURE_API_KEY")
        )
    else:
        raise ValueError(f"Unsupported provider: {LLM_PROVIDER}")

# --- Agent Initialization ---
selected_model = initialize_model()



root_agent = Agent(
    name="aint_agent",
    model=selected_model,

#    model="gemini-2.0-flash",
    description="Agent select tool for calling the tools.",
#    instruction="You are a helpful agent who can select the tool to answer user questions.",
    instruction=system_agent_prompt,
    tools=[mcp_tool],  # Pass the toolset directly to the agent
    before_agent_callback=opik_tracer.before_agent_callback,
    after_agent_callback=opik_tracer.after_agent_callback,
    before_model_callback=opik_tracer.before_model_callback,
    after_model_callback=opik_tracer.after_model_callback,
    before_tool_callback=opik_tracer.before_tool_callback,
    after_tool_callback=opik_tracer.after_tool_callback,
)


async def async_main():
  session_service = InMemorySessionService()
  artifacts_service = InMemoryArtifactService()

  session = await session_service.create_session(
      state={}, app_name='mcp_filesystem_app', user_id='user_fs'
  )

  query="Greet John"
  
  #query = "please use search query machine learning to search paper in arxiv"

#  query = "please find user code repository in github"
  print(f"User Query: '{query}'")
  content = types.Content(role='user', parts=[types.Part(text=query)])
  runner = Runner(
      app_name='mcp_filesystem_app',
      agent=root_agent,
      artifact_service=artifacts_service,
      session_service=session_service,
  )

  print("Running agent...")
  events_sync =  runner.run_async(
      session_id=session.id, user_id=session.user_id, new_message=content
  )

  async for event in events_sync:
    print(f"Event received: {event}")
  
  print("Agent run finished.")

  # Attempt to find and call a cleanup method for MCPToolset if it exists.
  # This is speculative. The ADK documentation should clarify MCPToolset cleanup.
  if hasattr(mcp_tool, 'close'):
      print("Closing MCPToolset via close()...")
      if asyncio.iscoroutinefunction(mcp_tool.close):
          await mcp_tool.close()
      else:
          mcp_tool.close()
      print("MCPToolset close() called.")
  elif hasattr(mcp_tool, 'shutdown'):
      print("Closing MCPToolset via shutdown()...")
      if asyncio.iscoroutinefunction(mcp_tool.shutdown):
          await mcp_tool.shutdown()
      else:
          mcp_tool.shutdown()
      print("MCPToolset shutdown() called.")
  else:
      print("MCPToolset does not have a standard close() or shutdown() method. Relaying on script exit for cleanup.")
  
  print("Cleanup complete (or relying on script exit).")

if __name__ == '__main__':
    print("start agent")
    import os
    cdr=os.path.dirname(__file__)
    env_path=os.path.join(cdr, ".env")
    load_dotenv(env_path)

    get_access_token()

    try:
        asyncio.run(async_main())
    except Exception as e:
        print(f"An error occurred: {e}")

        """
        
        """



