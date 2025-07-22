#!/bin/bash

# Set variables
export REGION="europe-west6"
export SERVICE_NAME="mcp-salesforce-server"

# Deploy the service directly from source
echo "Deploying to Cloud Run from source..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --port=8000 \
  --timeout=300 \
  --set-env-vars="PYTHONUNBUFFERED=1,MCP_STDIO_ENABLED=true,MCP_DEBUG=true" \
  --set-secrets="SALESFORCE_USERNAME=salesforce-username:latest,SALESFORCE_PASSWORD=salesforce-password:latest,SALESFORCE_SECURITY_TOKEN=salesforce-token:latest"

echo "Deployment completed!"
