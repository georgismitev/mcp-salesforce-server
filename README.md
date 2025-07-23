# MCP Salesforce Connector

A Model Context Protocol (MCP) server implementation for Salesforce integration, allowing LLMs to interact with Salesforce data through SOQL queries and SOSL searches. This project provides Docker containerization for easy deployment.

## Recent Updates

- **New Streaming Server**: Added SSE-based streaming MCP server as the main entry point for Docker workflow
- **Health Check Endpoints**: Added /health and /metrics endpoints for Docker health checks
- **Debugging Support**: Added debug mode for troubleshooting (`--debug` flag)
- **Clean Docker Workflow**: Added scripts for clean Docker management
- **Improved Error Handling**: Better error handling and logging for MCP server communication
- **Multiple Deployment Options**: Support for both Cloud Run (serverless) and VM deployment methods

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

## Deployment Options

This server can be deployed in two ways:

1. **Google Cloud Run (Serverless)**: For a fully managed serverless experience.
   - See [DEPLOYMENT-CLOUD-RUN.md](DEPLOYMENT-CLOUD-RUN.md) for detailed instructions.

2. **Google Compute Engine VM**: For more consistent performance and easier troubleshooting.
   - See [DEPLOYMENT-VM.md](DEPLOYMENT-VM.md) for detailed instructions.

Note: There are some known issues with Salesforce authentication in Cloud Run environments. If you encounter authentication problems with Cloud Run, the VM deployment option is recommended as a workaround.

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
   ./scripts/run_mcp_server.sh --port 8080
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

4. **Restart the server if needed**:
   ```bash
   ./scripts/restart_mcp_server.sh
   ```

## Configuration

### Salesforce Authentication Methods

This server supports two authentication methods:

- **OAuth (Recommended):** Set `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` as environment variables. 
- **Username/Password (Legacy):** If `SALESFORCE_ACCESS_TOKEN` and `SALESFORCE_INSTANCE_URL` are not set, the server will fall back to using `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, and `SALESFORCE_SECURITY_TOKEN`.

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

## Clean Start

To completely clean up all Docker resources related to this project and start fresh:

```bash
# Clean up all Docker containers and images
./scripts/cleanup_docker.sh

# Rebuild and start the container
./scripts/run_mcp_server.sh
```

This will remove all containers and images related to the MCP server and give you a clean starting point.
