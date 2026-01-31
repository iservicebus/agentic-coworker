# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy agent_ops package first
COPY agent_ops /app/agent_ops

# Copy integrator source code to agent_ops/src
# Only the source code is needed from integrator - all operational config stays in agent_ops
COPY integrator/src/integrator /app/agent_ops/src/integrator

# Install agent_ops (which now includes integrator)
WORKDIR /app/agent_ops
RUN pip install --no-cache-dir -e .

# Note: .env file is mounted at runtime via docker-compose volumes
# The load_env() function expects .env at /app/agent_ops/.env

# Set the working directory to where the app will run
WORKDIR /app/agent_ops

# Set Python path to include the src directory
ENV PYTHONPATH=/app/agent_ops/src:$PYTHONPATH

# Set entry point to run agent_ops CLI
ENTRYPOINT ["python", "-m", "agent_ops"]

# Default command (shows help if no args provided)
CMD ["--help"]
