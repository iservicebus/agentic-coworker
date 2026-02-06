import requests
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from typing import Optional, Dict, Any
import base64
from email.mime.text import MIMEText

from mcp import types
from mcp.shared.context import RequestContext




# Replace with your actual values
#KEYCLOAK_URL = "http://localhost:8888"
KEYCLOAK_URL = "http://host.docker.internal:8888"

REALM = "default"
CLIENT_ID = "agent-client"
#USERNAME = "agent-dev"
USERNAME = "dev"
PASSWORD = "securepass" # Make sure this is a secure password for your test user


AGENT_ID="agent-dev"
AGENT_SECRET="securepass"



def get_token_by_user():
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    payload = {
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD

    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code != 200:
        print(response.text)
        raise Exception("Failed to get token")
    return response.json()["access_token"]

def get_access_token_by_client():
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": AGENT_ID,
        "client_secret": AGENT_SECRET
    }

    response = requests.post(token_url, data=data)

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

def get_auth_headers(AGENT_ID:str=USERNAME):
    #access_token = get_access_token_by_client()
    access_token = get_token_by_user()

    print("Access token acquired.")

    # === Step 2: Send API request with token and client ID ===
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Tenant": "default",        
        "X-Agent-ID": AGENT_ID
    }
    return headers


async def test_tool_calling(session):

        print("Listing tools...")
        response = await session.list_tools()

        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        print("\n=== Call Tool: provider url ===")
        result = await session.call_tool("get_auth_provider_url", {"aint_path":{"provider_name":"linkedin"}})
        print(result)


        print("\n=== Call Tool: greet_user ===")
        result = await session.call_tool("generate_greeting", {"aint_body":{"name": "Bob"}})
        print(result)




        # print("\n=== Call Tool: fred ===")
        # result = await session.call_tool("fred-search", {"query":{"search_text": "canada"}})
        # print(result)


        # print("\n=== Call Tool: alpha ===")
        # result = await session.call_tool("alpha_vantage_time_series_intraday", {"query":{"symbol": "IBM"}})
        # print(result)

        # print("\n=== Call Tool: arxiv ===")
        # result = await session.call_tool("arxiv", {"query":{"search_query":"all:quantum+computing", "start":0, "max_results":3}})
        # print(result)



        # print("=== List Tools ===")
        # print("\nConnected to server with tools:", [tool for tool in available_tools])

        # print("\n=== Call Tool: email body url ===")
        # result = await session.call_tool("get_raw_email_body", {"body":{"sender": "jingnan.zhou@gmail.com", "recipient": "jingnan.zhou@gmail.com", "subject": "test", "body": "test only"}})
        # print(result)


        # print("\n=== Call Tool: provider url ===")
        # result = await session.call_tool("get_auth_provider_url", {"path":{"provider_name":"linkedin"}})
        # print(result)


        # print("\n=== Call Tool: linkedin userinfo ===")
        # result = await session.call_tool("LinkedInUserInfo", {})
        # print(result)


        # print("\n=== Call Tool: send gmail message ===")

        # sender = "your-email@gmail.com"
        # recipient = "jingnan.zhou@gmail.com"
        # subject = "Test Email"
        # body = "Hello from Python and Gmail API!"

        # # Create a MIMEText email message
        # message = MIMEText(body)
        # message['To'] = recipient
        # message['From'] = sender
        # message['Subject'] = subject
        # # Encode the message in base64url format (without padding)
        # raw_bytes = base64.urlsafe_b64encode(message.as_bytes())
        # raw_str = raw_bytes.decode().rstrip('=')



        # raw_body= { 'raw': raw_str }
        # result = await session.call_tool("Gmail_SendMessage", {"body":raw_body})
        # print(result)



        # print("\n=== Call Tool: github user ===")
        # result = await session.call_tool("GetAuthenticatedUser", {})
        # print(result)




        # print("\n=== Call Tool: sec ===")
        # result = await session.call_tool("search_sec_filings", {"body":{"query": "SpaceX", "formTypes": ["8-K", "10-Q"],"startDate": "2020-01-01","endDate": "2023-12-31"}})
        # print(result)


        # print("\n=== Call Tool: github repos ===")
        # result = await session.call_tool("github-repos", {})
        # print(result)




        # print("\n=== Call Tool: add_numbers ===")
        # result = await session.call_tool("add-service", {"body":{"a": 3, "b": 4}})
        # print(result)

        # print("\n=== Call Tool: greet_user ===")
        # result = await session.call_tool("greet_user", {"body":{"name": "Bob"}})
        # print(result)



async def main_sse():
    server_url = "http://0.0.0.0:6666/sse"
    _streams_context = None
    _session_context = None
    session: Optional[ClientSession] = None
    headers=get_auth_headers(AGENT_ID)


    async def refresh_tools():
        try:
            resp = await session.list_tools()
            names = [t.name for t in resp.tools]
            print("✅ tools now:", names)
        except Exception as e:
            print("refresh_tools error:", e)

    async def refresh_prompts():
        try:
            res = await session.list_prompts()
            print("prompts:", [p.name for p in res.prompts])
        except Exception as e:
            print("refresh_prompts error:", e)

    async def refresh_resources():
        try:
            res = await session.list_resources()
            print("resources:", [r.name for r in res.resources])
        except Exception as e:
            print("refresh_resources error:", e)


    # Single-arg handler (your SDK shape). Do NOT await session calls here.
    async def on_message(notification: types.ServerNotification) -> None:
        body = getattr(notification, "root", None)

        if isinstance(body, types.ToolListChangedNotification):
            print("🔔 tools/list_changed — scheduling refresh")
            asyncio.create_task(refresh_tools())   # <-- schedule, don’t await
            return

        if isinstance(body, types.PromptListChangedNotification):
            asyncio.create_task(refresh_prompts())  # implement similar to tools
            return

        if isinstance(body, types.ResourceListChangedNotification):
            asyncio.create_task(refresh_resources())  # implement similar
            return

    try:
        # Create SSE client connection

   # 1) Connect via SSE
        _streams_ctx = sse_client(url=server_url, headers=headers)
        read_stream, write_stream = await _streams_ctx.__aenter__()


        # 2) Create the MCP ClientSession with our message handler
        _session_ctx = ClientSession(
            read_stream,
            write_stream,
            message_handler=on_message,  # 👈 register handler here
        )
        session = await _session_ctx.__aenter__()


        await session.initialize()

        # List available tools to verify connection
        print("Initialized SSE client...")
        notify_data={ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }
        
        #response = requests.post("http://127.0.0.1:6666/notify", headers=headers,  json=notify_data)


        #rscs=await session.list_resources()
        
        await test_tool_calling(session)

        
        # --- Long-running wait to keep the client connected and listening ---
        print("\n=== Client Running and Listening for Notifications ===")
        print("Press Ctrl+C to gracefully shut down the client.")
        
        # Wait indefinitely. This is the main point of modification to keep the event loop alive.
        # It waits until the task is cancelled (e.g., via KeyboardInterrupt).
        await asyncio.Future() 


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



if __name__ == "__main__":
    # Wrap in outer try to handle run-time exceptions
    try:
        asyncio.run(main_sse())
    except KeyboardInterrupt:
        print("Program interrupted by user (Ctrl+C)")
    except asyncio.CancelledError:
        print("CancelledError raised after asyncio.run shutdown")
    except Exception as e:
        print(f"Unhandled exception during shutdown: {e}")

