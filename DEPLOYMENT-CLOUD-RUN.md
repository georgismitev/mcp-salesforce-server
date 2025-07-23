# Deploying MCP Salesforce Server to Google Cloud Run

This guide provides step-by-step instructions for deploying your MCP Salesforce Server to Google Cloud Platform (GCP) using Cloud Run (serverless).

## Deploy to Cloud Run (Serverless)

### Prerequisites

- A Google Cloud Platform account with billing enabled
- gcloud CLI installed on your local machine
- Docker installed locally (optional)

### Deployment Steps

#### Step 1: Install and Configure Google Cloud SDK

```bash
# Install gcloud CLI if not already installed
# macOS: https://cloud.google.com/sdk/docs/install-sdk#mac
# Linux: https://cloud.google.com/sdk/docs/install-sdk#linux
# Windows: https://cloud.google.com/sdk/docs/install-sdk#windows

# Initialize and authenticate
gcloud init
gcloud auth login

# Get your project ID (note this for future use)
export PROJECT_ID=$(gcloud config get-value project)
echo "Your project ID is: $PROJECT_ID"

# Set your project ID if needed
# gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com secretmanager.googleapis.com appengine.googleapis.com
```

#### Step 2: Create App Engine Application

Cloud Run requires an App Engine application to be set up in your project. This is required even if you don't plan to use App Engine directly.

```bash
# Create an App Engine application in the europe-west6 region
gcloud app create --region=europe-west

# Note: App Engine doesn't support all regions that Cloud Run does.
# The command above will create the App Engine application in the closest available region.
```

#### Step 3: Create Secrets in Secret Manager

```bash
# Create secrets for Salesforce credentials
# Using printf instead of echo for better security (avoids command history)
printf "your-salesforce-username" | gcloud secrets create salesforce-username --data-file=-
printf "your-salesforce-password" | gcloud secrets create salesforce-password --data-file=-
printf "your-salesforce-security-token" | gcloud secrets create salesforce-token --data-file=-

# Grant Cloud Run service access to the secrets
# First, get your Project ID
export PROJECT_ID=$(gcloud config get-value project)

# Get your project number (needed for service account identification)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
echo "Your project number is: $PROJECT_NUMBER"

# The Cloud Run service uses the default Compute Engine service account
export SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Default Compute service account: $SERVICE_ACCOUNT"

# Grant access to each secret
gcloud secrets add-iam-policy-binding salesforce-username \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding salesforce-password \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding salesforce-token \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

#### Step 4: Deploy to Cloud Run Directly from Source

```bash
# Set the region
export REGION=europe-west6
export PROJECT_ID=$(gcloud config get-value project)

# Deploy directly from your local source
gcloud run deploy mcp-salesforce-server 
  --source . \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --port=8080 \
  --timeout=120 \
  --set-env-vars="PYTHONUNBUFFERED=1,LOG_LEVEL=info" \
  --set-secrets="SALESFORCE_USERNAME=salesforce-username:latest,SALESFORCE_PASSWORD=salesforce-password:latest,SALESFORCE_SECURITY_TOKEN=salesforce-token:latest" \
```

#### Step 5: Verify Deployment

```bash
# Get the deployed service URL
export REGION=europe-west6
gcloud run services describe mcp-salesforce-server \
  --region=$REGION \
  --format="value(status.url)"
```

#### Step 6: Set Up Claude to Use Your Deployed MCP Server

Update your Claude configuration file with the following:

```json
{
  "mcpServers": {
    "salesforce-gcp": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp-salesforce-server-rybcvp7ala-oa.a.run.app"]
    }
  }
}
```

Replace `CLOUD_RUN_SERVICE_URL` with the URL you got from the previous step.

#### Step 7: Monitor and Troubleshoot

```bash
# Set default region (convenient for subsequent commands)
gcloud config set run/region europe-west6

# View logs
export PROJECT_ID=$(gcloud config get-value project)

gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mcp-salesforce-server" \
  --limit=50 \
  --format="table(timestamp, severity, textPayload)"

# Check service details
gcloud run services describe mcp-salesforce-server

# List Cloud Run Services Across All Regions
gcloud run services list --platform=managed --project=$(gcloud config get-value project) --format="table(location, name)"

# Get the container image currently in use
gcloud run services describe mcp-salesforce-server \
    --platform=managed \
    --region=$(gcloud config get-value run/region) \
    --project=$(gcloud config get-value project) \
    --format="value(spec.template.spec.containers[0].image)"
```

#### Step 8: Update the Deployment (If Needed)

If you make changes to your code:

```bash
# Set the region and project ID again if needed
export REGION=europe-west6
export PROJECT_ID=$(gcloud config get-value project)

# Redeploy with the same command
gcloud run deploy mcp-salesforce-server \
  --source . \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --port=8080 \
  --timeout=120 \
  --set-env-vars="PYTHONUNBUFFERED=1,LOG_LEVEL=info" \
  --set-secrets="SALESFORCE_USERNAME=salesforce-username:latest,SALESFORCE_PASSWORD=salesforce-password:latest,SALESFORCE_SECURITY_TOKEN=salesforce-token:latest"
```

#### Step 9: Cleanup (Optional)

If you need to delete the service:

```bash
# Set the region
export REGION=europe-west6
export PROJECT_ID=$(gcloud config get-value project)

# Get container image details
IMAGE_URL=$(gcloud run services describe mcp-salesforce-server \
  --region=$REGION \
  --format="value(spec.template.spec.containers[0].image)")

echo "Container image: $IMAGE_URL"

# Delete the container image (CAUTION: This permanently deletes the image)
gcloud artifacts docker images delete $IMAGE_URL --quiet

# Example of deleting a specific image by digest and its tags
# gcloud artifacts docker images delete europe-west6-docker.pkg.dev/mcp-salesforce-server/cloud-run-source-deploy/mcp-salesforce-server@sha256:6a...37 --delete-tags
```

## Known Issues with Cloud Run Deployment

When deploying to Cloud Run, there are some known issues with Salesforce authentication:

1. **SOAP Authentication Failures**: 
   - Authentication using the simple-salesforce library may fail in Cloud Run environments
   - The same code works in VM environments, suggesting an environment-specific issue

2. **Potential Root Causes**:
   - Network constraints in serverless environments
   - Differences in how HTTPS requests are handled, particularly for older SOAP endpoints
   - Ephemeral IP addresses used in Cloud Run

3. **Workarounds**:
   - Deploy to a VM instead (see DEPLOYMENT-VM.md)
   - Test with both simple-salesforce and raw SOAP implementations to isolate the issue

## Testing Cloud Run vs. VM Deployments

For troubleshooting authentication issues:

1. Set up the same server in both environments (Cloud Run and VM)
2. Use identical code, credentials, and configurations
3. Test authentication in both environments
4. Compare logs and responses
5. If authentication succeeds in VM but fails in Cloud Run, the issue is likely environment-specific

For more details on VM deployment, see DEPLOYMENT-VM.md.
