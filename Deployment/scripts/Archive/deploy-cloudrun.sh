#!/bin/bash

# Cloud Run Deployment Script for Avisk Core Services
# Usage: ./deploy-cloudrun.sh [PROJECT_ID] [REGION] [ENVIRONMENT]

set -e  # Exit on any error

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
ENVIRONMENT=${3:-"development"}
SERVICE_NAME="avisk-core-services-${ENVIRONMENT}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/avisk-core-services"

echo "🚀 Deploying Avisk Core Services to Cloud Run"
echo "=============================================="
echo "📋 Project ID: ${PROJECT_ID}"
echo "🌍 Region: ${REGION}"
echo "🏗️ Environment: ${ENVIRONMENT}"
echo "🐳 Image: ${IMAGE_NAME}"
echo ""

# Validate environment
if [[ ! "${ENVIRONMENT}" =~ ^(development|test|production)$ ]]; then
    echo "❌ Error: Invalid environment '${ENVIRONMENT}'"
    echo "✅ Valid environments: development, test, production"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed or not in PATH"
    echo "📥 Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not logged in to gcloud"
    echo "🔐 Run: gcloud auth login"
    exit 1
fi

# Set project
echo "🔧 Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Get current date for build info
BUILD_DATE=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Build and deploy using Cloud Build
echo "🏗️  Starting Cloud Build deployment..."
gcloud builds submit \
    --config=Deployment/cloudbuild-cloudrun.yaml \
    --substitutions=_REGION=${REGION},_ENVIRONMENT=${ENVIRONMENT},_BUILD_DATE="${BUILD_DATE}" \
    .

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format="value(status.url)")

echo ""
echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "🏥 Health Check: ${SERVICE_URL}/health"
echo ""
echo "📊 To view logs: gcloud logs tail \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --log-filter=\"severity>=INFO\""
echo "📈 To view metrics: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics"