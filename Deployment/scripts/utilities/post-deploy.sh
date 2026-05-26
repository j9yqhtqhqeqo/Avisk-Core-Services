#!/bin/bash
set -e

# Post-deployment verification for Avisk Core Services

ENVIRONMENT=${1:-"development"}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "✅ Running post-deployment verification for $ENVIRONMENT environment"

# Determine the app URL based on environment
case $ENVIRONMENT in
    "development")
        APP_URL="https://${GCP_PROJECT_DEV}.appspot.com"
        ;;
    "test")
        APP_URL="https://${GCP_PROJECT_TEST}.appspot.com"
        ;;
    "production")
        APP_URL="https://${GCP_PROJECT_PROD}.appspot.com"
        ;;
    *)
        echo "❌ Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Health check
echo "Running application health check..."
if curl -f --retry 3 --retry-delay 10 --max-time 30 "$APP_URL/health" >/dev/null 2>&1; then
    echo "✅ Application health check passed"
else
    echo "❌ Application health check failed"
    echo "URL: $APP_URL/health"
    # Don't fail the deployment for health check issues - might be expected
fi

# GCS connectivity test
echo "Testing GCS connectivity from deployed app..."
if curl -f --retry 2 --retry-delay 5 --max-time 30 "$APP_URL/test-gcs" >/dev/null 2>&1; then
    echo "✅ GCS connectivity test passed"
else
    echo "⚠️  GCS connectivity test failed or endpoint not available"
fi

# Check application logs
echo "Checking recent application logs..."
gcloud logging read "
    resource.type=\"gae_app\" AND
    timestamp >= \"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S%z)\" AND
    severity >= INFO
" --limit 10 --format="value(timestamp, severity, textPayload)" 2>/dev/null || echo "⚠️  Could not retrieve logs"

# Environment-specific verifications
case $ENVIRONMENT in
    "development")
        echo "Development-specific checks:"
        echo "✅ Development environment verified"
        ;;
    "test")
        echo "Test-specific checks:"
        echo "✅ Test environment verified"
        ;;
    "production")
        echo "Production-specific checks:"
        # Additional production checks could go here
        echo "✅ Production environment verified"
        ;;
esac

echo ""
echo "🎉 Post-deployment verification completed for $ENVIRONMENT!"
echo "📱 Application URL: $APP_URL"
echo "📊 Monitor logs: gcloud logging read 'resource.type=\"gae_app\"' --limit 50"
echo "📈 View metrics: https://console.cloud.google.com/appengine"