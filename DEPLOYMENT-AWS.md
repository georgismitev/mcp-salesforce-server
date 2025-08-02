# AWS Deployment Guide

This document summarizes the IAM roles, deployment steps, and best practices for deploying the MCP Salesforce server to AWS using App Runner and ECR.

## IAM Roles Overview

### 1. AppRunnerECRAccessRole
- **Purpose:**
  - Allows AWS App Runner to pull (read) container images from your private Amazon ECR repository.
- **Type:**
  - IAM Role (named `AppRunnerECRAccessRole` or `service-role/AppRunnerECRAccessRole`)
- **Trust Relationship:**
  - Trusted entity: `build.apprunner.amazonaws.com`
- **Permissions:**
  - Policy: `AmazonEC2ContainerRegistryReadOnly`
- **Used by:**
  - Referenced in the App Runner service's `AuthenticationConfiguration` as `AccessRoleArn`.

### 2. AWS CLI Deployment Role (User or Group with iam:PassRole)
- **Purpose:**
  - Allows a user or automation (e.g., CI/CD, CLI) to create/update App Runner services and assign the `AppRunnerECRAccessRole` to them.
- **Type:**
  - IAM User or Group
- **Permissions:**
  - `AWSAppRunnerFullAccess` (for App Runner management)
  - `AmazonEC2ContainerRegistryFullAccess` (for ECR management)
  - `iam:PassRole` permission for the `AppRunnerECRAccessRole` ARN
- **Used by:**
  - Any user or automation running the deployment script.

## Deployment Steps

You can follow the manual steps below, or simply use the deployment script: `scripts/deploy_sf_login_to_aws.sh` which automates the entire process.

1. **Build the Docker image locally:**
   ```sh
   docker build -t sf-login-test .
   ```
2. **Log in to Amazon ECR:**
   ```sh
   aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com
   ```
3. **Create the ECR repository if it doesn't exist:**
   ```sh
   aws ecr create-repository --repository-name sf-login-test --region eu-central-1
   # (ignore error if it already exists)
   ```
4. **Delete all images from the ECR repository before pushing the new image:**
   ```sh
   IMAGE_IDS=$(aws ecr list-images --repository-name sf-login-test --region eu-central-1 --query 'imageIds[*]' --output json)
   if [ "$IMAGE_IDS" != "[]" ]; then
     aws ecr batch-delete-image --repository-name sf-login-test --region eu-central-1 --image-ids "$IMAGE_IDS"
   fi
   ```
5. **Tag and push the image to ECR:**
   ```sh
   docker tag sf-login-test:latest <AWS_ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com/sf-login-test:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com/sf-login-test:latest
   ```
6. **Remove non-running App Runner services:**
   ```sh
   SERVICE_ARNS=$(aws apprunner list-services --region eu-central-1 --query 'ServiceSummaryList[?Status!=`RUNNING`].ServiceArn' --output text)
   for arn in $SERVICE_ARNS; do
     aws apprunner delete-service --service-arn "$arn" --region eu-central-1 || true
   done
   ```
7. **Deploy to AWS App Runner:**
   ```sh
   aws apprunner create-service \
     --service-name sf-login-test-$(date +%s) \
     --source-configuration "ImageRepository={ImageIdentifier=<AWS_ACCOUNT_ID>.dkr.ecr.eu-central-1.amazonaws.com/sf-login-test:latest,ImageRepositoryType=ECR},AutoDeploymentsEnabled=true,AuthenticationConfiguration={AccessRoleArn=arn:aws:iam::<AWS_ACCOUNT_ID>:role/AppRunnerECRAccessRole}" \
     --region eu-central-1
   ```
8. **Set Salesforce credentials as environment variables in the App Runner service settings.**

---

For more details, see the deployment script and AWS documentation on [App Runner IAM roles](https://docs.aws.amazon.com/apprunner/latest/dg/manage-iam.html).
