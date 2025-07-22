#!/bin/bash

# Clean up script for MCP Salesforce Server Docker resources
echo "Cleaning up Docker resources for MCP Salesforce Server..."

# Stop and remove containers
echo "Stopping and removing containers..."
docker stop $(docker ps -a -q --filter name=mcp-salesforce-server) 2>/dev/null || true
docker rm $(docker ps -a -q --filter name=mcp-salesforce-server) 2>/dev/null || true

# Remove images
echo "Removing Docker images..."
docker images -a | grep mcp-salesforce-server | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

# Clean up any dangling images
echo "Removing dangling images..."
docker image prune -f

# Verify cleanup
echo -e "\nVerifying cleanup:"
echo "Remaining containers:"
docker ps -a | grep mcp || echo "No MCP containers found."
echo -e "\nRemaining images:"
docker images | grep mcp || echo "No MCP images found."

echo -e "\nCleanup complete!"
