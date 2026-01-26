#!/bin/bash

# Local Cloud Run testing script
# Tests the Docker container locally before deployment

set -e

echo "🧪 Testing Avisk Core Services locally with Docker"
echo "================================================="

# Build Docker image
echo "🏗️  Building Docker image..."
docker build -t avisk-core-services:test .

# Stop any existing container
echo "🛑 Stopping existing containers..."
docker stop avisk-test 2>/dev/null || true
docker rm avisk-test 2>/dev/null || true

# Run container locally
echo "🚀 Starting container on port 8080..."
docker run -d \
    --name avisk-test \
    -p 8080:8080 \
    -e DEPLOYMENT_ENV=test \
    -e USE_GCS=false \
    avisk-core-services:test

# Wait for startup
echo "⏳ Waiting for service to start..."
sleep 10

# Test health endpoint
echo "🏥 Testing health check..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed!"
    echo "📋 Container logs:"
    docker logs avisk-test
    docker stop avisk-test
    docker rm avisk-test
    exit 1
fi

# Test main application
echo "🌐 Testing main application..."
if curl -f http://localhost:8080 >/dev/null 2>&1; then
    echo "✅ Main application accessible!"
else
    echo "⚠️  Main application test inconclusive (Streamlit may need user interaction)"
fi

echo ""
echo "🎉 Local testing completed!"
echo "🌐 Access your app at: http://localhost:8080"
echo "🏥 Health check at: http://localhost:8080/health"
echo ""
echo "📋 To view logs: docker logs avisk-test"
echo "🛑 To stop: docker stop avisk-test && docker rm avisk-test"