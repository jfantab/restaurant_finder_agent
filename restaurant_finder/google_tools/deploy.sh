#!/bin/bash
# Deploy Google Places MCP Server to Cloud Run

set -e  # Exit on error

# Configuration
PROJECT_ID="gcloudaccelerateproject"
REGION="us-west1"
SERVICE_NAME="google-places-mcp"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Google Places MCP Server to Cloud Run${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Step 1: Set the project
echo -e "\n${GREEN}📋 Step 1: Setting GCP project...${NC}"
gcloud config set project ${PROJECT_ID}

# Step 2: Enable required APIs
echo -e "\n${GREEN}🔧 Step 2: Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com

# Step 3: Deploy to Cloud Run (from source)
echo -e "\n${GREEN}🚢 Step 3: Deploying to Cloud Run from source...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-secrets "GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest"

# Step 4: Get the service URL
echo -e "\n${GREEN}✅ Step 4: Deployment complete!${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\n📍 Service URL: ${SERVICE_URL}"
echo -e "\n🔧 MCP Server Endpoint: ${SERVICE_URL}/sse"
echo -e "\n💡 Set environment variable:"
echo -e "   export GOOGLE_PLACES_MCP_URL=\"${SERVICE_URL}/sse\""
echo -e "\n💡 Usage in agent configuration:"
echo -e "   from google_tools import get_google_places_cloud_toolset"
echo -e "   toolset = get_google_places_cloud_toolset(\"${SERVICE_URL}/sse\")"
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
