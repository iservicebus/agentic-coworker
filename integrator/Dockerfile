# Stage 1: Builder
FROM mcr.microsoft.com/playwright:v1.57.0-jammy AS builder

WORKDIR /app

# Install system dependencies including git (needed for git-based pip installs)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --upgrade pip

# Copy dependency files and source code
COPY pyproject.toml setup.cfg README.md ./
COPY src ./src

# Install the project dependencies
RUN pip3 install --no-cache-dir -e .

# Stage 2: Runner
FROM mcr.microsoft.com/playwright:v1.57.0-jammy AS runner

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/pyproject.toml /app/setup.cfg /app/README.md ./
COPY config ./config

# Create a non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 6060

# Define environment variables
ENV PYTHONPATH=/app/src

# Run the application
CMD ["python3", "-m", "integrator.main"]
