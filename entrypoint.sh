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

echo "===== Selecting execution mode ====="

# Check which test mode to run
if [ "${RUN_MODE}" = "test_soap_login" ]; then
    echo "===== Running Salesforce SOAP Login Test ====="
    # Run the test_sf_soap_login.py script that tests raw SOAP authentication
    exec python ./scripts/test_sf_soap_login.py
elif [ "${RUN_MODE}" = "test_login" ]; then
    echo "===== Running Salesforce Standard Login Test ====="
    # Run the test_sf_login.py script that uses simple-salesforce
    exec python ./scripts/test_sf_login.py
else
    # Regular server mode
    echo "===== Server endpoints ====="
    echo "SSE endpoint: http://0.0.0.0:${PORT:-8080}/sse"
    echo "Health check: http://0.0.0.0:${PORT:-8080}/health"
    echo "Metrics: http://0.0.0.0:${PORT:-8080}/metrics"
    echo "===== Starting server ====="

    # Run the streaming server directly
    # Using exec replaces the current process with the Python process
    # so that signals like SIGTERM are properly passed to the Python process
    exec python -m src.salesforce.streaming_mcp_server \
      --host 0.0.0.0 \
      --port ${PORT:-8080} \
      --log-level ${LOG_LEVEL:-info}
fi
