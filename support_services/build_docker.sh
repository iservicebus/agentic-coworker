#!/bin/bash

# Build the support-services Docker image
echo "Building support-services Docker image..."
docker build -t ghcr.io/jingnanzhou/support-services:latest .

if [ $? -eq 0 ]; then
    echo "Docker image built successfully!"
    echo "Run './start_docker.sh' to start the container"
else
    echo "Docker build failed!"
    exit 1
fi
