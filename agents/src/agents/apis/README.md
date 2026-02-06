# Agent Chat REST API

OAuth-protected REST API for agent chat functionality with session-based conversation management.

## Overview

This API provides endpoints for creating chat sessions and interacting with AI agents. All endpoints are protected with OAuth authentication using Keycloak, and conversations are maintained through session management with LangGraph checkpointing.

## Features

- **OAuth Protection**: All endpoints require valid JWT tokens from Keycloak
- **Session Management**: Thread-safe session handling with automatic cleanup
- **Conversation Persistence**: LangGraph checkpointing maintains conversation history
- **MCP Integration**: Connects to MCP server for tool access
- **Multi-user Support**: Each user can have multiple concurrent sessions

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  FastAPI     │─────▶│  Keycloak   │
│             │      │  (OAuth)     │      │  (Auth)     │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Session     │
                     │  Manager     │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐      ┌─────────────┐
                     │  BaseAgent   │─────▶│  MCP Server │
                     │  (LangGraph) │      │  (Tools)    │
                     └──────────────┘      └─────────────┘
```

## API Endpoints

### 1. Create Session
**POST** `/chat/sessions`

Creates a new chat session for the authenticated user.

**Headers:**
```
Authorization: Bearer <token>
X-Agent-ID: <agent-id>
```

**Request Body:**
```json
{
  "agent_id": "optional-agent-id"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "thread_id": "uuid",
  "user_id": "username",
  "agent_id": "agent-id",
  "created_at": "2026-01-15T14:30:00",
  "message": "Session created successfully"
}
```

### 2. Send Message
**POST** `/chat/message`

Sends a message to the agent in an existing session.

**Headers:**
```
Authorization: Bearer <token>
X-Agent-ID: <agent-id>
```

**Request Body:**
```json
{
  "session_id": "uuid",
  "message": "Your message here"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "user_message": "Your message here",
  "agent_response": "Agent's response",
  "messages": [
    {
      "role": "user",
      "content": "Your message here"
    },
    {
      "role": "assistant",
      "content": "Agent's response"
    }
  ]
}
```

### 3. Get Session Info
**GET** `/chat/sessions/{session_id}`

Retrieves information about a specific session.

**Headers:**
```
Authorization: Bearer <token>
X-Agent-ID: <agent-id>
```

**Response:**
```json
{
  "session_id": "uuid",
  "user_id": "username",
  "agent_id": "agent-id",
  "thread_id": "uuid",
  "created_at": "2026-01-15T14:30:00",
  "last_accessed": "2026-01-15T14:35:00",
  "metadata": {}
}
```

### 4. List User Sessions
**GET** `/chat/sessions`

Lists all active sessions for the authenticated user.

**Headers:**
```
Authorization: Bearer <token>
X-Agent-ID: <agent-id>
```

**Response:**
```json
[
  {
    "session_id": "uuid",
    "user_id": "username",
    "agent_id": "agent-id",
    "thread_id": "uuid",
    "created_at": "2026-01-15T14:30:00",
    "last_accessed": "2026-01-15T14:35:00",
    "metadata": {}
  }
]
```

### 5. Delete Session
**DELETE** `/chat/sessions/{session_id}`

Deletes a chat session.

**Headers:**
```
Authorization: Bearer <token>
X-Agent-ID: <agent-id>
```

**Response:**
```json
{
  "session_id": "uuid",
  "message": "Session deleted successfully"
}
```

### 6. Health Check
**GET** `/health`

Returns server health status and active session count.

**Response:**
```json
{
  "status": "healthy",
  "active_sessions": 5
}
```

## Setup and Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=6000

# IAM/OAuth Configuration
IAM_URL=http://localhost:8888
REALM=default

# MCP Server Configuration
MCP_URL=http://localhost:6666/sse

# Azure OpenAI Configuration
LC_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_OPENAI_MODEL=gpt-5
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the `.env` file is configured with your settings.

### Running the Server

#### Development Mode
```bash
python -m agents.apis.api_server
```

#### Production Mode
```bash
uvicorn agents.apis.api_server:app --host 0.0.0.0 --port 8080
```

## Authentication Flow

1. **Obtain Token**: Get a JWT token from Keycloak using client credentials or user login
2. **Include Headers**: Add `Authorization: Bearer <token>` and `X-Agent-ID: <agent-id>` to all requests
3. **Token Validation**: The API validates the token against Keycloak's JWKS endpoint
4. **User Identification**: The `preferred_username` claim is used to identify the user

### Example Token Request (Client Credentials)

```bash
curl -X POST "http://localhost:8888/realms/default/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=agent-dev" \
  -d "client_secret=securepass"
```

## Session Management

### Session Lifecycle

1. **Creation**: Sessions are created via POST `/chat/sessions`
2. **Usage**: Each message updates the session's `last_accessed` timestamp
3. **Expiration**: Sessions expire after 60 minutes of inactivity (configurable)
4. **Cleanup**: A background task runs every 10 minutes to remove expired sessions
5. **Deletion**: Users can manually delete sessions via DELETE endpoint

### Thread Safety

The `SessionManager` uses thread locks to ensure safe concurrent access to session data.

### Conversation Persistence

- Each session has a unique `thread_id` used for LangGraph checkpointing
- Conversation history is maintained across multiple messages
- The `InMemorySaver` checkpointer stores conversation state in memory

## Error Handling

The API returns standard HTTP status codes:

- **200**: Success
- **401**: Unauthorized (invalid or missing token)
- **403**: Forbidden (session doesn't belong to user)
- **404**: Not Found (session not found or expired)
- **500**: Internal Server Error

Error responses include a `detail` field with more information:

```json
{
  "detail": "Session not found or expired"
}
```

## Security Considerations

1. **Token Validation**: All tokens are validated against Keycloak's public keys
2. **Session Ownership**: Users can only access their own sessions
3. **CORS**: Configure `allow_origins` appropriately for production
4. **HTTPS**: Use HTTPS in production environments
5. **Token Expiration**: Tokens have expiration times enforced by Keycloak

## Testing

### Using cURL

1. Get a token:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8888/realms/default/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=agent-dev" \
  -d "client_secret=securepass" | jq -r '.access_token')
```

2. Create a session:
```bash
SESSION=$(curl -s -X POST "http://localhost:8080/chat/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Agent-ID: agent-dev" \
  -H "Content-Type: application/json" \
  -d '{}' | jq -r '.session_id')
```

3. Send a message:
```bash
curl -X POST "http://localhost:8080/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Agent-ID: agent-dev" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"message\": \"Hello, agent!\"}"
```

### Using Python

```python
import requests

# Get token
token_response = requests.post(
    "http://localhost:8888/realms/default/protocol/openid-connect/token",
    data={
        "grant_type": "client_credentials",
        "client_id": "agent-dev",
        "client_secret": "securepass"
    }
)
token = token_response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}",
    "X-Agent-ID": "agent-dev"
}

# Create session
session_response = requests.post(
    "http://localhost:8080/chat/sessions",
    headers=headers,
    json={}
)
session_id = session_response.json()["session_id"]

# Send message
message_response = requests.post(
    "http://localhost:8080/chat/message",
    headers=headers,
    json={
        "session_id": session_id,
        "message": "Hello, agent!"
    }
)
print(message_response.json())
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check token is valid and not expired
   - Verify IAM_URL and REALM are correct
   - Ensure Keycloak is running

2. **500 Failed to connect to MCP server**
   - Verify MCP_URL is correct
   - Ensure MCP server is running
   - Check agent credentials are valid

3. **404 Session not found**
   - Session may have expired (60 min timeout)
   - Verify session_id is correct
   - Check session belongs to authenticated user

## Development

### Project Structure

```
src/agents/apis/
├── __init__.py           # Module initialization
├── api_server.py         # Main FastAPI application
├── chat_apis.py          # Chat endpoint implementations
├── session_manager.py    # Session management logic
└── README.md            # This file

src/agents/utils/
├── oauth.py             # OAuth token validation
├── llm.py               # LLM initialization
├── logger.py            # Logging utilities
└── env.py               # Environment loading
```

### Adding New Endpoints

1. Define request/response models in `chat_apis.py`
2. Implement endpoint function with `@chat_router` decorator
3. Add OAuth protection with `Depends(validate_token)`
4. Update this README with endpoint documentation

## License

See project root for license information.
