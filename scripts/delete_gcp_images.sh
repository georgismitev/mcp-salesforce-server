echo 'Before'
gcloud artifacts docker images list europe-west6-docker.pkg.dev/$(gcloud config get-value project)/cloud-run-source-deploy --format="value(DIGEST)"  2>/dev/null

echo 'Deleting'
for DIGEST in $(gcloud artifacts docker images list europe-west6-docker.pkg.dev/$(gcloud config get-value project)/cloud-run-source-deploy --format="value(DIGEST)"  2>/dev/null); do
  echo "Deleting: europe-west6-docker.pkg.dev/mcp-salesforce-server/cloud-run-source-deploy/mcp-salesforce-server@$DIGEST"
  gcloud artifacts docker images delete "europe-west6-docker.pkg.dev/mcp-salesforce-server/cloud-run-source-deploy/mcp-salesforce-server@$DIGEST" --delete-tags --quiet
done

echo 'After'
gcloud artifacts docker images list europe-west6-docker.pkg.dev/$(gcloud config get-value project)/cloud-run-source-deploy --format="value(DIGEST)"  2>/dev/null