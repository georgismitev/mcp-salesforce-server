#!/bin/bash
# deploy_sf_soap_login_test.sh - Deploy a test container to Cloud Run that tests raw SOAP login

# Set default values
REGION=${REGION:-"europe-west6"}
SERVICE_NAME=${SERVICE_NAME:-"mcp-sf-soap-login-test"}

# Get the project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"

# Deploy to Cloud Run with RUN_MODE=test_soap_login
echo "Deploying $SERVICE_NAME to Cloud Run in $REGION..."

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --timeout=120 \
  --set-env-vars="PYTHONUNBUFFERED=1,RUN_MODE=test_soap_login" \
  --set-secrets="SALESFORCE_USERNAME=salesforce-username:latest,SALESFORCE_PASSWORD=salesforce-password:latest,SALESFORCE_SECURITY_TOKEN=salesforce-token:latest"

echo ""
echo "Deployment complete. To check the SOAP login test results, run:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit=50"
echo ""
echo "Look for 'SUCCESS!' in the logs to confirm the SOAP authentication is working."
