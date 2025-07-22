# MCP Salesforce Connector

A Model Context Protocol (MCP) server implementation for Salesforce integration, allowing LLMs to interact with Salesforce data through SOQL queries and SOSL searches. This project provides Docker containerization for easy deployment.

## Recent Updates

- **New Streaming Server**: Added SSE-based streaming MCP server as the main entry point for Docker workflow
- **Health Check Endpoints**: Added /health and /metrics endpoints for Docker health checks
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
- SSE-based streaming server for real-time communication
- Health check endpoints for container monitoring

## Docker Setup

This project includes scripts for running the MCP server in a Docker container:

### Using Docker Script

1. **Start the server**:
   ```bash
   ./scripts/run_mcp_server.sh
   ```
   
   Additional options:
   ```bash
   ./scripts/run_mcp_server.sh --debug --port 8080 --log-level debug
   ```

### Using Streaming Server Locally

1. **Start the streaming server**:
   ```bash
   ./scripts/run_streaming_server.sh --port 8080
   ```

   Access the SSE endpoint at `http://localhost:8080/sse`

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
```

## Streaming Server Architecture

This project uses an SSE (Server-Sent Events) based streaming server as the main entry point for Docker deployments. The streaming server offers several advantages over the traditional stdio-based MCP server:

- **Web-based communication**: Uses HTTP and SSE for communication instead of stdio, making it more suitable for web-based clients and Docker environments
- **Health monitoring**: Provides `/health` and `/metrics` endpoints for monitoring the server's status
- **Persistent connections**: Maintains persistent connections with clients, allowing for real-time updates
- **Docker-friendly**: Designed to work seamlessly in containerized environments

### Endpoints

- `/sse`: The main SSE endpoint for MCP protocol communication
- `/health`: Health check endpoint that returns status 200 if the server is running properly
- `/metrics`: Provides additional metrics about the server's state

### Environment Variables

The streaming server uses the following environment variables:

- `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, `SALESFORCE_SECURITY_TOKEN`: Salesforce credentials (username-based authentication)
- `SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_INSTANCE_URL`: Salesforce credentials (token-based authentication)
- `PORT`: The port the server listens on (default: 8080)
- `LOG_LEVEL`: Set logging level (default: info, options: debug, info, warning, error)
- `MCP_DEBUG`: Enable debug logging (default: false)

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
