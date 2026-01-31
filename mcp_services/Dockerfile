# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy dependency files and source code
COPY pyproject.toml setup.cfg README.md ./
COPY src ./src

# Install the project dependencies
RUN pip install --no-cache-dir -e .

# Stage 2: Runner
FROM python:3.12-slim AS runner

WORKDIR /app

# Install only minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/pyproject.toml /app/setup.cfg /app/README.md ./

# Create a non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 6666

# Define environment variables
ENV PYTHONPATH=/app/src

# Run the application
CMD ["python", "-m", "mcp_services.main"]
