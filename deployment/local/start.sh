#!/bin/bash

# Get the absolute path to the project root (two levels up from deployment/local)
BASE_DIR=$(cd "$(dirname "$0")/../.."; pwd)

echo "Starting services in separate terminals..."

# Start integrator services in a new terminal
echo "Opening terminal for integrator..."
osascript -e "tell app \"Terminal\" to do script \"cd '$BASE_DIR/integrator' && echo 'Starting integrator...' && ./start.sh\""

# Start external REST services in a new terminal
echo "Opening terminal for external REST services..."
osascript -e "tell app \"Terminal\" to do script \"cd '$BASE_DIR/support_services' && echo 'Starting external REST services...' && ./start.sh\""

# Start MCP services in a new terminal
echo "Opening terminal for MCP services..."
osascript -e "tell app \"Terminal\" to do script \"cd '$BASE_DIR/mcp_services' && echo 'Starting MCP services...' && ./start.sh\""


# Start portal services in a new terminal
echo "Opening terminal for integrator..."
osascript -e "tell app \"Terminal\" to do script \"cd '$BASE_DIR/portal' && echo 'Starting portal...' && ./start.sh\""


echo "All services initiated in separate terminals."
echo "To stop the services, please close their respective terminal windows."
echo "start.sh finished."
