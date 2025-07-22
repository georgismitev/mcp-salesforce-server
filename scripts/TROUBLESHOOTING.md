### Troubleshooting the MCP Docker Container

If you encounter issues with the MCP server in Docker, here are some troubleshooting steps:

#### Container Exits Immediately
If the container exits immediately after starting, check:
1. View container logs with `docker logs mcp-salesforce-server-container`
2. Run `./restart_mcp_server.sh` to restart with our improved container settings

#### Connection Issues from Claude
If Claude cannot connect to the MCP server:
1. Verify the container is running with `docker ps`
2. Test the connection with `./verify_mcp_server.sh`
3. Make sure the configuration in Claude is correct
4. Check the Claude logs for connection errors

#### JSON Parsing Errors
If you see errors like `Unexpected token 'S', "Salesforce"... is not valid JSON` in Claude logs:
1. Run the fix script: `./fix_mcp_json_error.sh`
2. This fixes an issue where debug output is mixed with JSON responses
3. If the issue persists, run the server in debug mode: `./run_mcp_server.sh --debug`

#### Authentication Issues with Salesforce
If the server connects but Salesforce authentication fails:
1. Check your credentials in the `.env` file or Claude configuration
2. Test different authentication methods (OAuth vs Username/Password)
3. Verify your Salesforce security token is valid

#### Error: "Container not running"
If you see `Error response from daemon: Container ... is not running`:
1. The container may have crashed - check logs with `docker logs mcp-salesforce-server-container`
2. Restart the container with `./restart_mcp_server.sh`

For any other issues, please file a GitHub issue with details of your problem.
