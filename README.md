# MCP Salesforce Connector

A Model Context Protocol (MCP) server implementation for Salesforce integration, allowing LLMs to interact with Salesforce data through SOQL queries and SOSL searches. This project provides Docker containerization for easy deployment.

## Recent Updates

- **JSON Parsing Error Fix**: Implemented OutputFilter class to properly separate stdout (JSON) from stderr (debug messages)
- **Debugging Support**: Added debug mode for troubleshooting (`--debug` flag)
- **Clean Docker Workflow**: Added scripts for clean Docker management
- **Improved Error Handling**: Better error handling and logging for MCP server communication

## Features

- Execute SOQL (Salesforce Object Query Language) queries
- Perform SOSL (Salesforce Object Search Language) searches
- Retrieve metadata for Salesforce objects, including field names, labels, and types
- Retrieve, create, update, and delete records
- Execute Tooling API requests
- Execute Apex REST requests
- Make direct REST API calls to Salesforce

## Docker Setup

This project includes scripts for running the MCP server in a Docker container:

1. **Start the server**:
   ```bash
   ./scripts/run_mcp_server.sh
   ```

2. **Run in debug mode** (if needed):
   ```bash
   ./scripts/run_mcp_server.sh --debug
   ```

3. **Verify the server is working**:
   ```bash
   ./scripts/verify_mcp_server.sh
   ```

4. **Generate Claude configuration**:
   ```bash
   ./scripts/claude_setup.sh
   ```

5. **Restart the server if needed**:
   ```bash
   ./scripts/restart_mcp_server.sh
   ```

6. **Fix JSON parsing errors** (if needed):
   ```bash
   ./scripts/fix_mcp_json_error.sh
   ```


## Configuration

### Docker Configuration

The MCP server runs in a Docker container which simplifies deployment. The Docker setup:

- Uses Python 3.11 Alpine as a base image
- Installs necessary dependencies for the Salesforce connector
- Creates a default .env file for configuration
- Uses stdio communication (not HTTP/WebSocket)
- Properly separates stdout (JSON) from stderr (debug messages)
- Provides debug mode for troubleshooting

### Claude Configuration

To use this server with Claude, configure it in your `claude_desktop_config.json` file. Add the following entry to the `mcpServers` section:

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-salesforce-server-container",
        "python",
        "-u",
        "src/salesforce/server.py"
      ]
    }
  }
}
```

For your convenience, we provide a script to generate this configuration:
```bash
./scripts/claude_setup.sh
```

### Salesforce Authentication Methods

This server supports two authentication methods:

- **OAuth (Recommended):** Set `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` as environment variables. 
- **Username/Password (Legacy):** If `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` are not set, the server will fall back to using `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, and `SALESFORCE_SECURITY_TOKEN`.

To pass authentication details to the MCP server via Claude, include them in the env section:

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp-salesforce-server-container",
        "python", 
        "-u", 
        "src/salesforce/server.py"
      ],
      "env": {
        "SALESFORCE_USERNAME": "your_username",
        "SALESFORCE_PASSWORD": "your_password",
        "SALESFORCE_SECURITY_TOKEN": "your_security_token"
      }
    }
  }
}

## Troubleshooting

If you encounter issues with the MCP server, refer to the [TROUBLESHOOTING.md](scripts/TROUBLESHOOTING.md) file for common issues and solutions.

Common fixes:

1. **JSON Parsing Errors**: If Claude or other MCP clients report "not valid JSON" errors, run:
   ```bash
   ./scripts/fix_mcp_json_error.sh
   ```
   This ensures proper separation of debug messages from JSON communication.

2. **Debug Mode**: To see detailed server logs for troubleshooting:
   ```bash
   ./scripts/run_mcp_server.sh --debug
   ```

## Clean Start

To completely clean up all Docker resources related to this project and start fresh:

```bash
# Clean up all Docker containers and images
./scripts/cleanup_docker.sh

# Rebuild and start the container
./scripts/run_mcp_server.sh
```

This will remove all containers and images related to the MCP server and give you a clean starting point.
