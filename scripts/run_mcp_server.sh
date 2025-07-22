#!/bin/bash
# Run this script to get a local URL for the MCP server

echo "Setting up MCP server in Docker container..."

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH. Please install Docker first."
    exit 1
fi

# Define variables
CONTAINER_NAME="mcp-salesforce-server-container"
IMAGE_NAME="mcp-salesforce-server"
PORT=8000

# Ensure the .env file exists
if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    cat > .env << EOF
# Salesforce credentials
SALESFORCE_USERNAME=placeholder
SALESFORCE_PASSWORD=placeholder
SALESFORCE_SECURITY_TOKEN=placeholder
SALESFORCE_DOMAIN=login

# Server settings
PORT=8000
EOF
    echo "Please update the .env file with your Salesforce credentials."
    echo "You can edit the file now or press Enter to continue with placeholders."
    read -p "Press Enter to continue..."
fi

# Build the Docker image
echo "Building Docker image: $IMAGE_NAME..."
docker build -t $IMAGE_NAME .

# Stop and remove any existing container
echo "Cleaning up any existing containers..."
docker rm -f $CONTAINER_NAME 2>/dev/null

# Check for debug mode
if [ "$1" == "--debug" ]; then
  DEBUG_MODE=true
  echo "Running in DEBUG mode - container output will be shown"
else
  DEBUG_MODE=false
fi

# Run the container
echo "Running Docker container: $CONTAINER_NAME..."
if [ "$DEBUG_MODE" = true ]; then
  # Run in foreground with output visible
  docker run --name $CONTAINER_NAME -p $PORT:$PORT \
    -e PYTHONUNBUFFERED=1 \
    -e MCP_DEBUG=true \
    -v "$(pwd)/.env:/app/.env" \
    $IMAGE_NAME
else
  # Run in detached mode
  docker run -d --name $CONTAINER_NAME -p $PORT:$PORT \
    -e PYTHONUNBUFFERED=1 \
    -v "$(pwd)/.env:/app/.env" \
    $IMAGE_NAME
fi

# Wait for the container to start
echo "Waiting for the MCP server to start..."
sleep 2

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "Error: Container failed to start. Checking logs..."
    docker logs $CONTAINER_NAME
    exit 1
fi

echo "Container is running. Checking logs..."
docker logs $CONTAINER_NAME

# Print connection info
echo ""
echo "=========================================================="
echo " MCP SERVER RUNNING SUCCESSFULLY"
echo "=========================================================="
echo " The MCP server is now running in Docker."
echo " "
echo " This MCP server uses stdio communication, not HTTP/WebSocket."
echo " To use with your LLM application, configure as follows:"
echo " "
echo " In your claude_desktop_config.json, add:"
echo " {
  \"mcpServers\": {
    \"salesforce\": {
      \"command\": \"docker\",
      \"args\": [
        \"exec\",
        \"-i\",
        \"$CONTAINER_NAME\",
        \"python\", 
        \"-u\", 
        \"src/salesforce/server.py\"
      ]
    }
  }
}"
echo " "
echo " If you need to use specific credentials, add environment variables:"
echo " {
  \"mcpServers\": {
    \"salesforce\": {
      \"command\": \"docker\",
      \"args\": [
        \"exec\",
        \"-i\",
        \"$CONTAINER_NAME\",
        \"python\", 
        \"-u\", 
        \"src/salesforce/server.py\"
      ],
      \"env\": {
        \"SALESFORCE_USERNAME\": \"your_username\",
        \"SALESFORCE_PASSWORD\": \"your_password\",
        \"SALESFORCE_SECURITY_TOKEN\": \"your_security_token\"
      }
    }
  }
}"
echo " "
echo "=========================================================="
echo " To stop the server, run: docker stop $CONTAINER_NAME"
echo "=========================================================="
