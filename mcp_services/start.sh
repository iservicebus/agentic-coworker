# Ensure a clean installation
echo "Uninstalling existing mcp-services package (if any)..."
uv pip uninstall mcp-services  || echo "mcp-services not previously installed or uninstall failed."

echo "Installing mcp-services in editable mode with dependencies..."
uv pip install -e .

# Add the parent directory to PYTHONPATH to find sibling packages like 'integrator'
export PYTHONPATH="/Users/jingnan.zhou/workspace/aintegrator:$PYTHONPATH"
echo "PYTHONPATH set to: $PYTHONPATH"

echo "Running the server..."
python -m "mcp_services.main"
