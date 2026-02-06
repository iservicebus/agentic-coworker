#!/bin/bash

# Define the image name and container name
IMAGE_NAME="mcp-server"
CONTAINER_NAME="mcp-server-container"

# Stop and remove the existing container if it exists
echo "Stopping and removing existing container: $CONTAINER_NAME..."
docker stop $CONTAINER_NAME > /dev/null 2>&1
docker rm $CONTAINER_NAME > /dev/null 2>&1

# Build the Docker image
echo "Building Docker image: $IMAGE_NAME..."
docker build -t $IMAGE_NAME .

# Check if the build was successful
if [ $? -ne 0 ]; then
  echo "Docker build failed."
  exit 1
fi

# Run the Docker container in detached mode
echo "Running Docker container $CONTAINER_NAME in detached mode..."
docker run -d -p 6060:6060 --name $CONTAINER_NAME $IMAGE_NAME

# Check if the container started successfully
if [ $? -eq 0 ]; then
  echo "Container $CONTAINER_NAME started successfully on port 6060."
  echo "Access the service at http://localhost:6060"
else
  echo "Failed to start container $CONTAINER_NAME."
  exit 1
fi

exit 0
