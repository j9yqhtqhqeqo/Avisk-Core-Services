#!/bin/bash
set -e

# Main deployment script for Avisk Core Services
# Usage: ./deploy.sh [environment]

ENVIRONMENT=${1:-"development"}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/Deployment"

echo "🚀 Starting deployment to $ENVIRONMENT environment"
echo "📁 Project root: $PROJECT_ROOT"
echo "📦 Deployment directory: $DEPLOYMENT_DIR"

# Source environment-specific configuration
if [[ -f "$DEPLOYMENT_DIR/environments/$ENVIRONMENT.yaml" ]]; then
    echo "✅ Found environment config for $ENVIRONMENT"
else
    echo "❌ Environment config not found for $ENVIRONMENT"
    exit 1
fi

# Export environment variable
export DEPLOYMENT_ENV="$ENVIRONMENT"

# Run pre-deployment checks
echo "🔍 Running pre-deployment checks..."
if [[ -f "$DEPLOYMENT_DIR/scripts/pre-deploy.sh" ]]; then
    bash "$DEPLOYMENT_DIR/scripts/pre-deploy.sh" "$ENVIRONMENT"
else
    echo "⚠️  No pre-deployment checks found"
fi

# Deploy to Google Cloud
echo "☁️  Deploying to Google Cloud..."
cd "$PROJECT_ROOT"

case $ENVIRONMENT in
    "development")
        gcloud app deploy "$DEPLOYMENT_DIR/app.yaml" \
            --project="$GCP_PROJECT_DEV" \
            --version="dev-$(date +%Y%m%d-%H%M%S)" \
            --no-promote \
            --quiet
        ;;
    "test")
        gcloud app deploy "$DEPLOYMENT_DIR/app.yaml" \
            --project="$GCP_PROJECT_TEST" \
            --version="test-$(date +%Y%m%d-%H%M%S)" \
            --no-promote \
            --quiet
        ;;
    "production")
        echo "🔒 Production deployment requires confirmation"
        read -p "Deploy to PRODUCTION? (yes/no): " confirm
        if [[ $confirm == "yes" ]]; then
            gcloud app deploy "$DEPLOYMENT_DIR/app.yaml" \
                --project="$GCP_PROJECT_PROD" \
                --version="prod-$(date +%Y%m%d-%H%M%S)" \
                --promote \
                --quiet
        else
            echo "❌ Production deployment cancelled"
            exit 1
        fi
        ;;
    *)
        echo "❌ Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Run post-deployment verification
echo "✅ Running post-deployment verification..."
if [[ -f "$DEPLOYMENT_DIR/scripts/post-deploy.sh" ]]; then
    bash "$DEPLOYMENT_DIR/scripts/post-deploy.sh" "$ENVIRONMENT"
else
    echo "⚠️  No post-deployment verification found"
fi

echo "🎉 Deployment to $ENVIRONMENT completed successfully!"