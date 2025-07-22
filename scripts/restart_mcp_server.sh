#!/bin/bash
# restart_mcp_server.sh - Restart the MCP server container

CONTAINER_NAME="mcp-salesforce-server-container"

echo "Stopping existing container..."
docker stop $CONTAINER_NAME >/dev/null 2>&1 || true

echo "Removing existing container..."
docker rm $CONTAINER_NAME >/dev/null 2>&1 || true

echo "Restarting MCP server..."
./run_mcp_server.sh
