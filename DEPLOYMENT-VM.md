# VM Deployment Guide for MCP Salesforce Server

This guide provides step-by-step instructions for deploying the MCP Salesforce Server to a Google Compute Engine VM.

## Why Use VM Deployment?

- **Environment Comparison**: Helps diagnose if issues in Cloud Run are environment-specific
- **No Cold Starts**: VMs provide consistent performance without serverless cold starts
- **Full Network Control**: Direct control over networking and firewall settings
- **Debugging Capabilities**: Easy SSH access for troubleshooting

## Prerequisites

- Google Cloud Platform account with billing enabled
- `gcloud` CLI tool installed and configured
- Project with required APIs enabled (Compute Engine, Secret Manager)
- Salesforce credentials stored in Secret Manager

## Deployment Steps

### 1. Run the Deployment Script

The included `deploy_to_vm.sh` script automates the entire VM setup process:

```bash
cd scripts
./deploy_to_vm.sh
```

You can customize the deployment with these parameters:
- `--vm-name=name` - Custom VM name (default: "mcp-salesforce-server-vm")
- `--region=region` - GCP region (default: "europe-west6")
- `--zone=zone` - GCP zone (default: "europe-west6-a")
- `--machine-type=type` - VM machine type (default: "e2-small")

For example:
```bash
./deploy_to_vm.sh --zone=us-central1-a --machine-type=e2-medium
```

### 2. What the Script Does

1. **VM Creation**:
   - Creates a Debian 11 VM with the specified configuration
   - Sets up appropriate service account and scopes
   - Configures necessary tags for firewall rules

2. **Software Installation**:
   - Installs Docker and dependencies
   - Sets up Docker permissions correctly
   - Clones the repository code

3. **Credentials Setup**:
   - Retrieves Salesforce credentials from Secret Manager
   - Creates `.env` file with correct configuration

4. **Container Deployment**:
   - Builds Docker image from source
   - Runs container with host networking
   - Sets DEBUG mode and other environment variables
   - Verifies container is listening on all interfaces

5. **Network Configuration**:
   - Creates firewall rule to allow traffic on port 8080
   - Displays the external IP and available endpoints

### 3. Accessing the Server

After deployment completes, you'll see output showing:
- The VM's external IP address
- Available endpoints (SSE, health check, metrics)
- Instructions for connecting Claude to your server

### 4. Claude Configuration

Update your Claude configuration with:
```json
{
  "mcpServers": {
    "salesforce-gcp-vm": {
      "command": "npx", 
      "args": ["mcp-remote", "http://<EXTERNAL_IP>:8080/sse", "--allow-http"]
    }
  }
}
```

Note: The `--allow-http` flag is required since we're using HTTP instead of HTTPS.

### 5. Testing and Verification

1. **Health Check**:
   ```bash
   curl http://<EXTERNAL_IP>:8080/health
   ```

2. **Server Logs**:
   ```bash
   # SSH into the VM
   gcloud compute ssh mcp-salesforce-server-vm --zone=<zone>
   
   # View server logs
   sudo docker logs -f mcp-salesforce-container
   ```

3. **Network Verification**:
   ```bash
   # Check if server is listening on all interfaces
   sudo netstat -tulpn | grep 8080
   # Should show: 0.0.0.0:8080 (listening on all interfaces)
   ```

### 6. Troubleshooting

1. **Container Issues**:
   ```bash
   # Check container status
   sudo docker ps -a
   
   # Restart container if needed
   sudo docker restart mcp-salesforce-container
   ```

2. **Permission Problems**:
   ```bash
   # Fix Docker socket permissions
   sudo chmod 666 /var/run/docker.sock
   ```

3. **Firewall Settings**:
   ```bash
   # Verify firewall rules
   sudo gcloud compute firewall-rules list | grep mcp-server
   
   # Create or update rule if needed
   sudo gcloud compute firewall-rules create allow-mcp-server --allow tcp:8080 --target-tags http-server
   ```

4. **Checking Binding**:
   If the server is only listening on localhost (127.0.0.1) instead of all interfaces (0.0.0.0), you may need to modify the server code to bind to all interfaces.

### 7. Comparing with Cloud Run

When testing Salesforce authentication:
1. Test on the VM and verify authentication works
2. Compare with Cloud Run behavior to identify environment-specific issues
3. Look for network-related differences, especially with SOAP requests

## Cleanup

To delete the VM when finished:
```bash
gcloud compute instances delete mcp-salesforce-server-vm --zone=<zone>
```
