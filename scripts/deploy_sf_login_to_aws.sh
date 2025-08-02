#!/bin/bash
# Automated deployment of Salesforce login test image to AWS App Runner via ECR (eu-west-1)
# Usage: ./scripts/deploy_sf_login_to_aws.sh <AWS_ACCOUNT_ID>

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <AWS_ACCOUNT_ID>"
  exit 1
fi

AWS_ACCOUNT_ID="$1"
AWS_REGION="eu-central-1"
REPO_NAME="sf-login-test"
IMAGE_NAME="sf-login-test:latest"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
SCRIPT_PATH="scripts/test_sf_login.py"

# Remove old image if it exists
echo "Removing old Docker image (if exists)..."
docker rmi -f $IMAGE_NAME || true

echo "Building fresh Docker image..."
docker build -t $IMAGE_NAME .

echo "Logging in to Amazon ECR..."
echo $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION

echo "Deleting all images from ECR repository before pushing new image..."
IMAGE_IDS=$(aws ecr list-images --repository-name $REPO_NAME --region $AWS_REGION --query 'imageIds[*]' --output json)
if [ "$IMAGE_IDS" != "[]" ]; then
  aws ecr batch-delete-image --repository-name $REPO_NAME --region $AWS_REGION --image-ids "$IMAGE_IDS"
else
  echo "No images to delete."
fi

echo "Tagging image for ECR..."
docker tag $IMAGE_NAME $ECR_URI

echo "Pushing image to ECR..."
docker push $ECR_URI

echo "Removing non-running App Runner services..."
SERVICE_ARNS=$(aws apprunner list-services --region $AWS_REGION --query 'ServiceSummaryList[?Status!=`RUNNING`].ServiceArn' --output text)
for arn in $SERVICE_ARNS; do
  echo "Deleting App Runner service: $arn"
  aws apprunner delete-service --service-arn "$arn" --region $AWS_REGION || true
done

echo "Deploying to AWS App Runner..."
aws apprunner create-service \
  --service-name sf-login-test-$(date +%s) \
  --source-configuration "ImageRepository={ImageIdentifier=$ECR_URI,ImageRepositoryType=ECR},AutoDeploymentsEnabled=true,AuthenticationConfiguration={AccessRoleArn=arn:aws:iam::$AWS_ACCOUNT_ID:role/AppRunnerECRAccessRole}" \
  --region $AWS_REGION

echo "\nDeployment initiated. Check the AWS App Runner console for status."
echo "Set Salesforce credentials as environment variables in the App Runner service settings."
