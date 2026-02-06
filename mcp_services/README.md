# MCP Services Project

This project implements a dynamic MCP (Model-Context-Protocol) server in Python. It acts as a proxy, fetching tool definitions and configurations from a remote "integrator" service. This allows for dynamic addition and modification of tools without restarting the server.

## Key Features

- **Dynamic Tool Loading**: Tools are fetched from a remote service, allowing for real-time updates.
- **Tenant-Based Configuration**: Supports multi-tenancy with configurations fetched based on the tenant context.
- **OAuth 2.0 Integration**: Secures tool access through OAuth 2.0, managing tokens for different providers.
- **Multiple Transports**: Supports both `sse` (Server-Sent Events) and `stdio` for communication.
- **Proxy Layer**: Abstracts external API calls, routing them through a configurable proxy URL.

---

## 📁 Project Structure

```text
mcp_services/
├── pyproject.toml
├── setup.cfg
├── README.md
├── src/
│   └── mcp_services/
│       ├── servers/
│       │   ├── aint_mcp_provider.py  # Core MCP server logic
│       │   └── config.json           # Server configuration
│       └── utils/
│           ├── oauth.py              # OAuth token validation
│           ├── json_norm.py          # JSON normalization utilities
│           └── host.py               # Host utility functions
└── tests/
    └── test_mcp.py
```

---

## ⚙️ Configuration

The server can be configured using environment variables or by editing `src/mcp_services/servers/config.json`. Environment variables take precedence over the values in `config.json`.

### Environment Variables

You can set the following environment variables to configure the server:

- `PORT`: The port on which the server will run.
- `TRANSPORT`: The communication transport to use (`sse` or `stdio`).
- `AUTHORIZATION_ENABLED`: Set to `true` to enable OAuth 2.0 authorization.
- `AUTHORIZATION_HOST`: The base URL of the authorization service.
- `INTEGRATOR_URL`: The URL of the integrator service that provides tool definitions.
- `PROXY_URL`: The base URL for proxying external API calls.

For local development, you can create a `.env` file in the root of the project and add the variables there:

```
PORT=6666
TRANSPORT=sse
AUTHORIZATION_ENABLED=true
AUTHORIZATION_HOST=http://localhost:3000
INTEGRATOR_URL=http://localhost:6060
PROXY_URL=http://localhost
```

### `config.json`

If environment variables are not set, the server will fall back to the values in `src/mcp_services/servers/config.json`:

```json
{
  "port": 6666,
  "transport": "sse",
  "authorization_enabled": true,
  "authorization_host": "http://localhost:3000",
  "integrator_url":"http://localhost:6060",
  "proxy_url": "http://localhost"
}
```

---

## 🚀 Getting Started

### 📦 Installation

Install the project in editable mode:

```bash
pip install -e .
```

### ▶️ Running the Server

To run the MCP server, execute the main provider script:

```bash
python -m src.mcp_services.servers.aint_mcp_provider
```

The server will start using the settings from `config.json`.

---

## 🧪 Testing and Linting

### Run Tests

This project uses `pytest` for testing.

```bash
pip install pytest
pytest
```

### Type Checking with mypy

```bash
pip install mypy
mypy src/
```

### Code Formatting with Black

```bash
pip install black
black src/
```

### Linting with Ruff

```bash
pip install ruff
ruff check src --fix
