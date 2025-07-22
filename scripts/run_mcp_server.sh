#!/bin/bash
# Run this script to get a local URL for the MCP server using the streaming server

echo "Setting up MCP Salesforce Streaming Server in Docker container..."

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH. Please install Docker first."
    exit 1
fi

# Define variables
CONTAINER_NAME="mcp-salesforce-server-container"
IMAGE_NAME="mcp-salesforce-server"
PORT=8080
LOG_LEVEL="info"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --port) PORT="$2"; shift ;;
        --log-level) LOG_LEVEL="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Ensure the .env file exists
if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    cat > .env << EOF
# Salesforce credentials - either use username/password/token:
SALESFORCE_USERNAME=placeholder
SALESFORCE_PASSWORD=placeholder
SALESFORCE_SECURITY_TOKEN=placeholder

# Or use access token + instance URL:
# SALESFORCE_ACCESS_TOKEN=placeholder
# SALESFORCE_INSTANCE_URL=placeholder

# Server settings
PORT=8080
LOG_LEVEL=info
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
if [[ "$*" == *"--debug"* ]]; then
  DEBUG_MODE=true
  echo "Running in DEBUG mode - container output will be shown"
  LOG_LEVEL="debug"
else
  DEBUG_MODE=false
fi

# Run the container
echo "Running Docker container: $CONTAINER_NAME on port $PORT..."
if [ "$DEBUG_MODE" = true ]; then
  # Run in foreground with output visible
  docker run --name $CONTAINER_NAME -p $PORT:$PORT \
    -e PYTHONUNBUFFERED=1 \
    -e MCP_DEBUG=true \
    -e PORT=$PORT \
    -e LOG_LEVEL=$LOG_LEVEL \
    -v "$(pwd)/.env:/app/.env" \
    $IMAGE_NAME
else
  # Run in detached mode
  docker run -d --name $CONTAINER_NAME -p $PORT:$PORT \
    -e PYTHONUNBUFFERED=1 \
    -e PORT=$PORT \
    -e LOG_LEVEL=$LOG_LEVEL \
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
echo " MCP STREAMING SERVER RUNNING SUCCESSFULLY"
echo "=========================================================="
echo " The MCP Streaming Server is now running in Docker."
echo " "
echo " This MCP server uses SSE (Server-Sent Events) over HTTP, not stdio."
echo " "
echo " Available endpoints:"
echo "   - SSE endpoint:   http://localhost:$PORT/sse"
echo "   - Health check:   http://localhost:$PORT/health"
echo "   - Metrics:        http://localhost:$PORT/metrics"
echo " "
echo " To use with your LLM application that supports SSE-based MCP:"
echo " Configure your client to connect to: http://localhost:$PORT/sse"
echo " "
echo " For applications using stdio-based MCP connections:"
echo " You can still use the stdio interface by running:"
echo " "
echo " docker exec -i $CONTAINER_NAME python -u src/salesforce/server.py"
echo " "
echo " For debugging or checking logs:"
echo " docker logs $CONTAINER_NAME"
echo " "
echo " "
echo "=========================================================="
echo " To stop the server, run: docker stop $CONTAINER_NAME"
echo "=========================================================="
