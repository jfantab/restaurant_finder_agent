#!/bin/bash
# Grant Cloud Run service account access to Secret Manager secrets

set -e  # Exit on error

PROJECT_ID="gcloudaccelerateproject"
PROJECT_NUMBER="894009546149"
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Granting Secret Manager access to Cloud Run service account${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${GREEN}Service Account: ${SERVICE_ACCOUNT}${NC}"
echo -e "${GREEN}Granting 'Secret Manager Secret Accessor' role...${NC}\n"

# Grant access to each secret
for secret in APPLE_TEAM_ID APPLE_KEY_ID APPLE_PRIVATE_KEY; do
    echo -e "Granting access to: ${secret}"
    gcloud secrets add-iam-policy-binding ${secret} \
        --project=${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet

    if [ $? -eq 0 ]; then
        echo -e "  ✅ ${secret}"
    else
        echo -e "  ❌ Failed to grant access to ${secret}"
    fi
done

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Permissions granted!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\n${GREEN}Next step:${NC} Run ./deploy.sh again to deploy your MCP server"
