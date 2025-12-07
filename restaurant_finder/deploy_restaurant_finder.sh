#!/bin/bash
# Deploy the restaurant finder agent to Google Cloud

# Change to the restaurant_finder directory
cd "$(dirname "$0")" || exit 1

# Deploy to Vertex AI Agent Engine
adk deploy agent_engine \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-west1 \
  . \
  --agent_engine_config_file=.agent_engine_config.json
