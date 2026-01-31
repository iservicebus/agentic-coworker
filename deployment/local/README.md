# Local Development Deployment

This directory contains scripts for running all AIntegrator services locally in development mode (not in Docker containers).

## Overview

The local deployment runs each service in its own terminal window, making it easy to:
- View logs from each service separately
- Restart individual services
- Debug and develop locally
- Use local development tools

**Platform**: macOS only (uses AppleScript to manage Terminal windows)

## Prerequisites

1. **Support platform services must be running**:
   ```bash
   cd ../support-platform
   ./start.sh
   ```

2. **Each service must have its local environment configured**:
   - `agent-studio/.env.local` - Agent Studio environment
   - `integrator/.env` - Integrator environment
   - `mcp_services/.env` - MCP Services environment
   - `support_services/.env` - Support Services environment

3. **Dependencies installed for each service**:
   - Portal: `npm install` in portal/
   - Integrator: Python environment with dependencies
   - MCP Services: Python environment with dependencies
   - Support Services: Python environment with dependencies

4. **Each service must have a `start.sh` script** in its directory

## Services Started

The local deployment starts these services in separate terminal windows:

1. **Integrator** (Port 6060)
   - Main integration service
   - Terminal title: "AIIntegrator-Integrator"

2. **Support Services** (Port 5000)
   - Supporting API services
   - Terminal title: "AIIntegrator-SupportServices"

3. **MCP Services** (Port 6666)
   - Model Context Protocol services
   - Terminal title: "AIIntegrator-MCPServices"

4. **Agent Studio** (Port 3000)
   - Next.js frontend application
   - Terminal title: "AIIntegrator-AgentStudio"

## Quick Start

### Start All Services

```bash
cd deployment/local
./start.sh
```

This will:
1. Open 4 new terminal windows
2. Navigate to each service directory
3. Run the service's `start.sh` script
4. Each service runs in its own terminal with logs visible

### Stop All Services

```bash
cd deployment/local
./stop.sh
```

This will:
1. Find all terminal windows by their custom titles
2. Kill all processes in those terminals
3. Close the terminal windows

## Manual Service Control

### Start Individual Services

If you prefer to start services manually:

```bash
# Terminal 1 - Integrator
cd integrator
./start.sh

# Terminal 2 - Support Services
cd support_services
./start.sh

# Terminal 3 - MCP Services
cd mcp_services
./start.sh

# Terminal 4 - Agent Studio
cd agent-studio
./start.sh
```

### Stop Individual Services

Just close the terminal window or press `Ctrl+C` in the terminal running the service.

## Service Startup Order

The `start.sh` script starts services in this order:
1. Integrator (backend core)
2. Support Services (supporting APIs)
3. MCP Services (MCP protocol)
4. Agent Studio (frontend)

This order ensures dependencies are available when needed.

## Service Dependencies

### Support Platform (Required)
All services depend on the support platform infrastructure:
- PostgreSQL (database)
- Keycloak (authentication)
- Neo4j (graph database)
- ETCD (configuration)

**Make sure the support platform is running first!**

### Inter-Service Dependencies
- Agent Studio depends on Integrator for backend APIs
- MCP Services may depend on Integrator
- Support Services work independently

## Environment Configuration

Each service uses its local environment file:

### Agent Studio
```bash
# agent-studio/.env.local
NEXTAUTH_URL=http://localhost:3000
INTEGRATOR_BASE_URL=http://localhost:6060
DATABASE_URL=postgresql://user:password@localhost:5432/agent-studio
# ... other variables
```

### Integrator
```bash
# integrator/.env
PORT=6060
IAM_URL=http://localhost:8888
MCP_URL=http://localhost:6666/sse
DATABASE_URL=postgresql://user:password@localhost:5432/agent-studio
# ... other variables
```

### MCP Services
```bash
# mcp_services/.env
PORT=6666
IAM_URL=http://localhost:8888
INTEGRATOR_URL=http://localhost:6060
DATABASE_URL=postgresql://user:password@localhost:5432/agent-studio
# ... other variables
```

### Support Services
```bash
# support_services/.env
INTEGRATOR_URL=http://localhost:3000
IAM_URL=http://localhost:8888
# ... other variables
```

## Development Workflow

### Typical Development Flow

1. **Start support platform** (once per development session):
   ```bash
   cd deployment/support-platform
   ./start.sh
   ```

2. **Start application services**:
   ```bash
   cd deployment/local
   ./start.sh
   ```

3. **Develop**:
   - Each service runs in its own terminal
   - View logs in real-time
   - Make code changes
   - Services may auto-reload (depends on service)

4. **Restart individual service** (if needed):
   - Close the terminal window
   - Manually run the service's `start.sh` again

5. **Stop all services** when done:
   ```bash
   cd deployment/local
   ./stop.sh
   ```

### Hot Reload

- **Agent Studio**: Next.js has hot reload enabled in development mode
- **Python services**: May require manual restart after code changes (depends on configuration)

## Accessing Services

Once running, services are available at:

| Service | URL |
|---------|-----|
| Agent Studio | http://localhost:3000 |
| Integrator | http://localhost:6060 |
| MCP Services | http://localhost:6666 |
| Support Services | http://localhost:5000 |

## Troubleshooting

### Services Not Starting

Check each terminal window for error messages. Common issues:

1. **Support platform not running**:
   ```bash
   cd deployment/support-platform
   docker-compose ps
   # Should show all services as "Up"
   ```

2. **Port already in use**:
   ```bash
   # Find what's using the port
   lsof -i :3000  # or :6060, :6666, :5000
   # Kill the process or change the port
   ```

3. **Dependencies not installed**:
   ```bash
   # Agent Studio
   cd agent-studio && npm install

   # Python services
   cd integrator && pip install -e .
   cd mcp_services && pip install -e .
   cd support_services && pip install -e .
   ```

4. **Environment files missing**:
   - Check that each service has its `.env` or `.env.local` file
   - Copy from `.env.example` if available

### stop.sh Not Working

If the stop script doesn't work:

```bash
# Manually find and kill processes
ps aux | grep -E "integrator|mcp_services|support_services|next"

# Kill by PID
kill <PID>

# Or force kill
kill -9 <PID>
```

### Terminal Windows Not Opening

Check Terminal permissions:
1. System Preferences → Privacy & Security → Automation
2. Ensure Terminal has permission to control itself

### Services Can't Connect

Check service URLs in environment files:
- Use `localhost` for local development
- Use correct ports (3000, 5000, 6060, 6666)
- Ensure support platform uses `localhost` (not `host.docker.internal`)

## Platform Limitations

### macOS Only

The scripts use AppleScript to control Terminal.app, which only works on macOS.

**For Linux/Windows**:
- Start each service manually in separate terminal windows
- Or adapt the scripts to use your platform's terminal control

### Terminal.app Only

The scripts are designed for macOS Terminal.app. If you use iTerm2 or another terminal:
- Start services manually
- Or adapt the scripts for your terminal

## Comparison with Docker Deployment

| Aspect | Local | Docker |
|--------|-------|--------|
| Startup Speed | Fast | Slower (container build) |
| Hot Reload | Yes (Agent Studio) | Depends on setup |
| Log Visibility | Separate terminals | `docker-compose logs` |
| Resource Usage | Lower | Higher |
| Isolation | Process-level | Container-level |
| Platform | macOS only | Cross-platform |
| Best For | Active development | Testing, consistency |

## Service Start Scripts

Each service must have a `start.sh` in its directory. Example:

### Agent Studio
```bash
# agent-studio/start.sh
npm run dev
```

### Python Services
```bash
# integrator/start.sh
python -m integrator.main
```

Check each service's documentation for the correct start command.

## Logs

Logs are visible in each service's terminal window in real-time.

To save logs to files, modify each service's `start.sh`:
```bash
# Example for integrator
python -m integrator.main 2>&1 | tee logs/integrator.log
```

## Development Tips

1. **Use separate terminal tabs/windows** instead of the scripts if you prefer more control

2. **Set terminal titles** manually for easy identification:
   ```bash
   echo -e "\033]0;My Service\007"
   ```

3. **Use tmux or screen** for persistent sessions:
   ```bash
   tmux new -s aintegrator
   # Split windows, start services
   ```

4. **Configure IDE run configurations** instead of using scripts:
   - VS Code: `.vscode/launch.json`
   - PyCharm: Run configurations
   - IntelliJ: Run configurations

## Support

For service-specific issues:
- Check the service's README
- View logs in the service's terminal window
- Check environment configuration

For support platform issues:
- See `../support-platform/README.md`
