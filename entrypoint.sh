#!/bin/sh
# entrypoint.sh - Wrapper script for MCP Streaming Server

# Set up proper signal handling
trap 'echo "Received SIGTERM, shutting down gracefully..."; exit 0' TERM
trap 'echo "Received SIGINT, shutting down gracefully..."; exit 0' INT

# Echo environment for debugging
echo "===== Starting MCP Salesforce Streaming Server ====="
echo "Python version: $(python --version)"
echo "Port: ${PORT:-8080}"
echo "Host: 0.0.0.0"
echo "Log level: ${LOG_LEVEL:-info}"

# Check simple-salesforce version
echo "===== Checking simple-salesforce version ====="
python -c "import simple_salesforce; print(f'simple-salesforce version: {getattr(simple_salesforce, \"__version__\", \"unknown\")}')"

# Check if environment variables are set
if [ -z "$SALESFORCE_USERNAME" ]; then
    echo "INFO: SALESFORCE_USERNAME is not set."
else
    echo "INFO: SALESFORCE_USERNAME is set."
fi

if [ -z "$SALESFORCE_PASSWORD" ]; then
    echo "INFO: SALESFORCE_PASSWORD is not set."
else
    echo "INFO: SALESFORCE_PASSWORD is set."
fi

if [ -z "$SALESFORCE_SECURITY_TOKEN" ]; then
    echo "INFO: SALESFORCE_SECURITY_TOKEN is not set."
else
    echo "INFO: SALESFORCE_SECURITY_TOKEN is set."
fi

if [ -z "$SALESFORCE_ACCESS_TOKEN" ]; then
    echo "INFO: SALESFORCE_ACCESS_TOKEN is not set."
else
    echo "INFO: SALESFORCE_ACCESS_TOKEN is set."
fi

if [ -z "$SALESFORCE_INSTANCE_URL" ]; then
    echo "INFO: SALESFORCE_INSTANCE_URL is not set."
else
    echo "INFO: SALESFORCE_INSTANCE_URL is set."
fi

# Check if environment variables are set
if [ -z "$SALESFORCE_USERNAME" ] && [ -z "$SALESFORCE_SECURITY_TOKEN" ]; then
    echo "WARNING: Neither SALESFORCE_USERNAME nor SALESFORCE_ACCESS_TOKEN are set."
    echo "The server will start, but connections to Salesforce will fail."
    echo "Please set either:"
    echo "  - SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN or"
    echo "  - SALESFORCE_ACCESS_TOKEN and SALESFORCE_INSTANCE_URL"
fi

# Create a log directory if it doesn't exist
mkdir -p /app/logs

echo "===== Server endpoints ====="
echo "SSE endpoint: http://0.0.0.0:${PORT:-8080}/sse"
echo "Health check: http://0.0.0.0:${PORT:-8080}/health"
echo "Metrics: http://0.0.0.0:${PORT:-8080}/metrics"
echo "===== Starting server ====="

# Set the debug flags based on environment variables
if [ "${DEBUG_SALESFORCE:-false}" = "true" ]; then
  SF_LOG_LEVEL="debug"
  echo "Salesforce debug logging enabled"
else
  SF_LOG_LEVEL="${SF_LOG_LEVEL:-$LOG_LEVEL}"
fi

if [ "${DEBUG_HTTP:-false}" = "true" ]; then
  HTTP_LOG_LEVEL="debug"
  echo "HTTP debug logging enabled"
else
  HTTP_LOG_LEVEL="${HTTP_LOG_LEVEL:-$LOG_LEVEL}"
fi

# Run the streaming server directly
# Using exec replaces the current process with the Python process
# so that signals like SIGTERM are properly passed to the Python process
exec python -m src.salesforce.streaming_mcp_server \
  --host 0.0.0.0 \
  --port ${PORT:-8080} \
  --log-level ${LOG_LEVEL:-info} \
  --sf-log-level ${SF_LOG_LEVEL:-info} \
  --http-log-level ${HTTP_LOG_LEVEL:-info}
