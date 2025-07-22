#!/bin/bash
# verify_mcp_server.sh - Test the MCP streaming server connection

CONTAINER_NAME="mcp-salesforce-server-container"
PORT=8080
HOST="localhost"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift
      shift
      ;;
    --host)
      HOST="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

echo "Verifying MCP streaming server container is running..."
if ! docker ps | grep -q $CONTAINER_NAME; then
  echo "ERROR: Container $CONTAINER_NAME is not running."
  exit 1
fi

echo "Container is running. Testing MCP streaming server endpoints..."

# Check health endpoint
echo "Checking health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/health)
if [ "$HEALTH_STATUS" = "200" ]; then
  echo "✅ Health check passed: $HOST:$PORT/health returned HTTP $HEALTH_STATUS"
  
  # If health check passed, get the actual health data
  HEALTH_DATA=$(curl -s http://$HOST:$PORT/health)
  echo "   Health data: $HEALTH_DATA"
else
  echo "❌ Health check failed: $HOST:$PORT/health returned HTTP $HEALTH_STATUS"
  echo "The server may not be running correctly."
fi

# Check metrics endpoint
echo "Checking metrics endpoint..."
METRICS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/metrics)
if [ "$METRICS_STATUS" = "200" ]; then
  echo "✅ Metrics check passed: $HOST:$PORT/metrics returned HTTP $METRICS_STATUS"
  
  # If metrics check passed, get the actual metrics data
  METRICS_DATA=$(curl -s http://$HOST:$PORT/metrics)
  echo "   Metrics data: $METRICS_DATA"
else
  echo "❌ Metrics check failed: $HOST:$PORT/metrics returned HTTP $METRICS_STATUS"
fi

# Check SSE endpoint
echo "Checking SSE endpoint exists (cannot fully validate SSE protocol)..."
SSE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/sse)
if [ "$SSE_STATUS" = "200" ] || [ "$SSE_STATUS" = "101" ]; then
  echo "✅ SSE endpoint check passed: $HOST:$PORT/sse is available"
else
  echo "❌ SSE endpoint check failed: $HOST:$PORT/sse returned HTTP $SSE_STATUS"
fi

# Verify stdio MCP still works
echo ""
echo "Testing stdio MCP connection through Docker (for backward compatibility)..."
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}},"id":1}' | \
  docker exec -i $CONTAINER_NAME python -u src/salesforce/server.py | head -n 3

echo ""
echo "Verifying container is still running..."
if docker ps | grep -q $CONTAINER_NAME; then
  echo "SUCCESS: Container is still running after tests!"
else
  echo "ERROR: Container stopped after tests."
  echo "Checking container logs..."
  docker logs $CONTAINER_NAME
  exit 1
fi

echo ""
echo "MCP streaming server verification complete. The server appears to be working correctly."
echo ""
echo "Available endpoints:"
echo "- SSE endpoint: http://$HOST:$PORT/sse"
echo "- Health check: http://$HOST:$PORT/health"
echo "- Metrics: http://$HOST:$PORT/metrics"
echo ""
echo "For SSE-based MCP applications, use the SSE endpoint."
echo "For stdio-based MCP applications, you can still use the stdio interface."
