#!/bin/bash
# deploy_to_vm.sh - Deploy the MCP Salesforce Server to a Google Compute Engine VM

# Default settings
VM_NAME=${VM_NAME:-"mcp-salesforce-server-vm"}
REGION=${REGION:-"europe-west6"}
ZONE=${ZONE:-"europe-west6-a"}
MACHINE_TYPE=${MACHINE_TYPE:-"e2-small"}
IMAGE_FAMILY=${IMAGE_FAMILY:-"debian-11"}
IMAGE_PROJECT=${IMAGE_PROJECT:-"debian-cloud"}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --vm-name=*)
      VM_NAME="${1#*=}"
      shift
      ;;
    --region=*)
      REGION="${1#*=}"
      shift
      ;;
    --zone=*)
      ZONE="${1#*=}"
      shift
      ;;
    --machine-type=*)
      MACHINE_TYPE="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown parameter: $1"
      echo "Usage: $0 [--vm-name=name] [--region=region] [--zone=zone] [--machine-type=type]"
      exit 1
      ;;
  esac
done

# Print header
echo "===== Deploying MCP Salesforce Server to a VM ====="
echo "VM Name: $VM_NAME"
echo "Region: $REGION"
echo "Zone: $ZONE"
echo "Machine Type: $MACHINE_TYPE"

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"

# Check if VM already exists
VM_EXISTS=$(gcloud compute instances list --filter="name=$VM_NAME" --format="value(name)")
if [ -n "$VM_EXISTS" ]; then
    echo "VM '$VM_NAME' already exists. Stopping and deleting..."
    gcloud compute instances delete $VM_NAME --zone=$ZONE --quiet
    echo "VM deleted."
fi

# Create a startup script for the VM
cat > startup-script.sh << 'EOF'
#!/bin/bash
# VM startup script for MCP Salesforce Server

# Install Docker
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Configure Docker to run without sudo
groupadd -f docker
usermod -aG docker $(whoami)
# Make sure Docker socket is accessible
chmod 666 /var/run/docker.sock

# Create app directory
mkdir -p /opt/mcp-salesforce-server
cd /opt/mcp-salesforce-server

# Clone the repository
git clone https://github.com/georgismitev/mcp-salesforce-server.git .

# Access secrets
export SALESFORCE_USERNAME=$(gcloud secrets versions access latest --secret="salesforce-username")
export SALESFORCE_PASSWORD=$(gcloud secrets versions access latest --secret="salesforce-password")
export SALESFORCE_SECURITY_TOKEN=$(gcloud secrets versions access latest --secret="salesforce-token")

# Create .env file
cat > .env << EOL
SALESFORCE_USERNAME=$SALESFORCE_USERNAME
SALESFORCE_PASSWORD=$SALESFORCE_PASSWORD
SALESFORCE_SECURITY_TOKEN=$SALESFORCE_SECURITY_TOKEN
PORT=8080
LOG_LEVEL=INFO
EOL

# Build Docker image and log results
echo "Building Docker image..."
docker build -t mcp-salesforce-server . > /tmp/docker_build.log 2>&1
if [ $? -ne 0 ]; then
  echo "ERROR: Docker build failed. See /tmp/docker_build.log for details"
  exit 1
fi
echo "Docker image built successfully"

# Run the standard MCP server
echo "Starting MCP container..."

# Check if the container already exists and remove it if needed
if docker ps -a --format "{{.Names}}" | grep -q "^mcp-salesforce-container$"; then
  echo "Container already exists, removing it first..."
  docker rm -f mcp-salesforce-container >> /tmp/docker_run.log 2>&1
fi

# Run the container
echo "Running container with environment values from .env file"
docker run -d --name mcp-salesforce-container \
  -e PYTHONUNBUFFERED=1 \
  -e SALESFORCE_USERNAME=$SALESFORCE_USERNAME \
  -e SALESFORCE_PASSWORD=$SALESFORCE_PASSWORD \
  -e SALESFORCE_SECURITY_TOKEN=$SALESFORCE_SECURITY_TOKEN \
  -e PORT=8080 \
  -e LOG_LEVEL=DEBUG \
  -e MCP_DEBUG=true \
  --network=host \
  mcp-salesforce-server > /tmp/docker_run.log 2>&1
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to start container. See /tmp/docker_run.log for details"
  exit 1
fi

# Verify the container is still running after a few seconds
echo "Waiting to verify container is stable..."
sleep 5
if docker ps | grep -q "mcp-salesforce-container"; then
  echo "Container is running stably."
  echo "Container started successfully. Container ID: $(docker ps -q -f name=mcp-salesforce-container)"
  
  # Check if the server is listening on the right interface
  echo "Checking server network binding..."
  if netstat -tulpn | grep 8080 | grep -q "0.0.0.0"; then
    echo "Server is properly listening on all interfaces"
  else
    echo "WARNING: Server might be listening only on localhost. Installing netcat to verify connectivity..."
    apt-get install -y netcat-openbsd
    
    # Test if port is reachable from outside
    nc -zv localhost 8080
    echo "Checking if health endpoint is responding..."
    curl -v http://localhost:8080/health
    
    echo "NOTE: If the server is only listening on localhost, external access will fail."
    echo "You might need to modify the server configuration to listen on 0.0.0.0 instead of 127.0.0.1"
  fi
else
  echo "Container failed to stay running. Checking logs..."
  docker logs mcp-salesforce-container > /tmp/container_logs.log 2>&1
  echo "Container logs saved to /tmp/container_logs.log"
  cat /tmp/container_logs.log
  exit 1
fi
EOF

# No sed replacement needed

# Create the VM
echo "Creating VM: $VM_NAME..."
gcloud compute instances create $VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")-compute@developer.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --create-disk=auto-delete=yes,boot=yes,device-name=instance-1,image=projects/$IMAGE_PROJECT/global/images/family/$IMAGE_FAMILY,mode=rw,size=10 \
  --metadata-from-file=startup-script=startup-script.sh \
  --tags=http-server,https-server

# Clean up temporary files
rm -f startup-script.sh

# Allow necessary traffic
echo "Creating firewall rule for MCP server on port 8080..."
# With host networking, the container binds directly to port 8080 on the host
# No port mapping is used, so we only need to allow traffic on port 8080
gcloud compute firewall-rules create allow-mcp-server --allow tcp:8080 --target-tags http-server --description "Allow MCP server traffic on port 8080" || true

# Get the VM's external IP
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo "===== Deployment Complete ====="
echo "VM External IP: $EXTERNAL_IP"

echo ""
echo "The MCP Salesforce Server is now running on your VM."
echo ""
echo "Available endpoints:"
echo "- SSE endpoint:   http://$EXTERNAL_IP:8080/sse"
echo "- Health check:   http://$EXTERNAL_IP:8080/health"
echo "- Metrics:        http://$EXTERNAL_IP:8080/metrics"
echo ""
echo "To use with Claude:"
echo "Update your Claude configuration with:"
echo "{\"mcpServers\": {\"salesforce-gcp-vm\": {\"command\": \"npx\", \"args\": [\"mcp-remote\", \"http://$EXTERNAL_IP:8080/sse\", \"--allow-http\"]}}}"

echo ""
echo "To SSH into the VM:"
echo "gcloud compute ssh $VM_NAME --zone=$ZONE"
