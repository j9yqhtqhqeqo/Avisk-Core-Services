#!/bin/bash
#
# Increase PostgreSQL temp_file_limit to 10GB
# Usage: ./increase-temp-limit.sh
#

set -e

# Configuration
INSTANCE_NAME="avisk-core-dev"
PROJECT_ID="avisk-ai-platform"
TEMP_LIMIT_KB="10485760"  # 10GB in KB

echo "========================================="
echo "Increasing temp_file_limit to 10GB"
echo "========================================="
echo "Instance: $INSTANCE_NAME"
echo "Project: $PROJECT_ID"
echo "Limit: ${TEMP_LIMIT_KB}KB (10GB)"
echo ""

# Get current flags
echo "📋 Current database flags:"
gcloud sql instances describe "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --format="value(settings.databaseFlags)"
echo ""

# Update the temp_file_limit flag
echo "⏳ Updating temp_file_limit..."
gcloud sql instances patch "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --database-flags=temp_file_limit="$TEMP_LIMIT_KB" \
    --quiet

echo ""
echo "✅ Successfully updated temp_file_limit to 10GB"
echo ""
echo "⚠️  Note: The instance may restart to apply the changes"
echo "    This could take a few minutes"
echo ""
echo "Verify the change:"
echo "  gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format='value(settings.databaseFlags)'"
