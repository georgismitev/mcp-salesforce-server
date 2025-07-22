#!/bin/bash
# claude_setup.sh - Generate Claude configuration for MCP server

CONTAINER_NAME="mcp-salesforce-server-container"
CONFIG_FILE="claude_salesforce_config.json"

echo "Generating Claude configuration for MCP Salesforce server..."

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
  echo "ERROR: Container $CONTAINER_NAME is not running."
  echo "Please run ./run_mcp_server.sh first."
  exit 1
fi

# Generate the configuration file
cat > $CONFIG_FILE << EOF
{
  "mcpServers": {
    "salesforce": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "$CONTAINER_NAME",
        "python",
        "-u",
        "src/salesforce/server.py"
      ]
    }
  }
}
EOF

echo "Configuration file generated: $CONFIG_FILE"
echo ""
echo "To use this with Claude:"
echo "1. Open Claude Desktop settings"
echo "2. Add the content of $CONFIG_FILE to your claude_desktop_config.json file"
echo "3. Restart Claude Desktop"
echo ""
echo "You can edit the configuration to include Salesforce credentials if needed."
