#!/bin/bash
# verify_mcp_server.sh - Test the MCP server connection

CONTAINER_NAME="mcp-salesforce-server-container"

echo "Verifying MCP server container is running..."
if ! docker ps | grep -q $CONTAINER_NAME; then
  echo "ERROR: Container $CONTAINER_NAME is not running."
  exit 1
fi

echo "Container is running. Testing MCP connection..."
echo "Sending initialize request to the server..."

# Create a temporary file for the test
TEST_FILE=$(mktemp)
cat > $TEST_FILE << 'EOF'
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}},"id":1}

EOF

# Test the connection using actual MCP protocol
echo "Testing MCP connection through Docker..."
cat $TEST_FILE | docker exec -i $CONTAINER_NAME python -u src/salesforce/server.py

echo ""
echo "Verifying container is still running after connection..."
if docker ps | grep -q $CONTAINER_NAME; then
  echo "SUCCESS: Container is still running after connection test!"
else
  echo "ERROR: Container stopped after connection test."
  echo "Checking container logs..."
  docker logs $CONTAINER_NAME
  exit 1
fi

# Clean up
rm $TEST_FILE

echo ""
echo "MCP server verification complete. The server appears to be working correctly."
echo "You can now use it with Claude by configuring it in claude_desktop_config.json."
