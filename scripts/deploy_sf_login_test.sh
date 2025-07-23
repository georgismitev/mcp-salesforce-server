#!/bin/bash
# deploy_sf_login_test.sh - Deploy a test container to Cloud Run that runs test_sf_login.py

# Set default values
REGION=${REGION:-"europe-west6"}
SERVICE_NAME=${SERVICE_NAME:-"mcp-sf-login-test"}

# Get the project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"

# Deploy to Cloud Run with RUN_MODE=test_login
echo "Deploying $SERVICE_NAME to Cloud Run in $REGION..."

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --timeout=120 \
  --set-env-vars="PYTHONUNBUFFERED=1,RUN_MODE=test_login" \
  --set-secrets="SALESFORCE_USERNAME=salesforce-username:latest,SALESFORCE_PASSWORD=salesforce-password:latest,SALESFORCE_SECURITY_TOKEN=salesforce-token:latest"

echo ""
echo "Deployment complete. "
echo "Look for 'SALESFORCE LOGIN TEST SUCCESSFUL' in the logs to confirm success."
