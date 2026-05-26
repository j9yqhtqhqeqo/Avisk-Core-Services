#!/bin/bash

# Deployment Verification Script for Avisk Core Services
# Usage: ./verify-deployment.sh [PROJECT_ID] [REGION] [ENVIRONMENT]

set -e  # Exit on any error

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
ENVIRONMENT=${3:-"development"}
SERVICE_NAME="avisk-core-services-${ENVIRONMENT}"

echo "🔍 Verifying Avisk Core Services deployment"
echo "============================================"
echo "📋 Project ID: ${PROJECT_ID}"
echo "🌍 Region: ${REGION}"
echo "🏗️ Environment: ${ENVIRONMENT}"
echo "📦 Service: ${SERVICE_NAME}"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

# Check if service exists
echo "🔎 Checking if service exists..."
if ! gcloud run services describe ${SERVICE_NAME} --region=${REGION} &>/dev/null; then
    echo "❌ Service ${SERVICE_NAME} not found in region ${REGION}"
    echo "📋 Available services:"
    gcloud run services list --region=${REGION} --format="table(metadata.name:label=SERVICE,status.url:label=URL)"
    exit 1
fi

# Get service details
echo "📊 Service Details:"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format="value(status.url)")

SERVICE_ENV=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format="table(spec.template.spec.template.spec.containers[0].env[].name,spec.template.spec.template.spec.containers[0].env[].value)" \
    | grep DEPLOYMENT_ENV | awk '{print $2}')

echo "🌐 Service URL: ${SERVICE_URL}"
echo "🏷️ Deployment Environment Variable: ${SERVICE_ENV}"

# Health check
echo ""
echo "🏥 Testing health endpoint..."
if curl -f --max-time 10 "${SERVICE_URL}/health" &>/dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "🔍 Try: curl -v ${SERVICE_URL}/health"
fi

# Verify environment matches
echo ""
if [[ "${SERVICE_ENV}" == "${ENVIRONMENT}" ]]; then
    echo "✅ Environment verification PASSED: Service is deployed to ${ENVIRONMENT}"
else
    echo "❌ Environment verification FAILED: Service shows ${SERVICE_ENV} but expected ${ENVIRONMENT}"
    exit 1
fi

echo ""
echo "🎉 Deployment verification completed successfully!"
echo "📈 View logs: gcloud logs tail \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --log-filter=\"severity>=INFO\""
echo "📊 View metrics: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics"