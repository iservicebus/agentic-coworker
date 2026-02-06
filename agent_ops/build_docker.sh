#!/bin/bash
# Build script for agent-ops Docker image

set -e

echo "Building agent-ops Docker image..."
docker build -t ghcr.io/jingnanzhou/agent-ops:latest -f Dockerfile ..

echo ""
echo "Build completed successfully!"
echo ""
echo "Usage examples (with utility container):"
echo "  docker exec agent-ops python -m agent_ops --help"
echo "  docker exec agent-ops python -m agent_ops init-seed"
echo "  docker exec agent-ops python -m agent_ops backup"
echo "  docker exec agent-ops python -m agent_ops restore --restore-from /app/data/backup_data/TIMESTAMP"
echo ""
echo "For more details, see QUICK_REFERENCE.md"
