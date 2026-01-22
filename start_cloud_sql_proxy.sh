#!/bin/bash

# Cloud SQL Auth Proxy Startup Script
# This script starts the Cloud SQL Auth Proxy to connect to the Avisk database

echo "🔌 Starting Cloud SQL Auth Proxy..."
echo "===================================="

# Configuration
INSTANCE_CONNECTION_NAME="avisk-ai-platform:us-central1:avisk-core-dev"
LOCAL_PORT="5434"
PROXY_ADDRESS="127.0.0.1:${LOCAL_PORT}"

echo "📋 Configuration:"
echo "   Instance: ${INSTANCE_CONNECTION_NAME}"
echo "   Local Address: ${PROXY_ADDRESS}"
echo "   Database: avisk-core-dev-db1"
echo ""

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "❌ cloud-sql-proxy is not installed or not in PATH"
    echo ""
    echo "📥 To install Cloud SQL Auth Proxy:"
    echo "   # Option 1: Download from Google Cloud"
    echo "   curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64"
    echo "   chmod +x cloud-sql-proxy"
    echo "   sudo mv cloud-sql-proxy /usr/local/bin/"
    echo ""
    echo "   # Option 2: Install via gcloud"
    echo "   gcloud components install cloud-sql-proxy"
    echo ""
    exit 1
fi

# Check if port is already in use
if lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t >/dev/null; then
    echo "⚠️  Port ${LOCAL_PORT} is already in use. Checking if it's cloud-sql-proxy..."
    EXISTING_PROCESS=$(lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN | grep -v PID)
    echo "   ${EXISTING_PROCESS}"
    echo ""
    read -p "Do you want to stop the existing process and restart? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 Stopping existing process on port ${LOCAL_PORT}..."
        PID=$(lsof -Pi :${LOCAL_PORT} -sTCP:LISTEN -t)
        kill ${PID}
        sleep 2
    else
        echo "❌ Cannot start proxy - port ${LOCAL_PORT} is in use"
        exit 1
    fi
fi

# Start the Cloud SQL Auth Proxy
echo "🚀 Starting Cloud SQL Auth Proxy..."
echo "   Press Ctrl+C to stop"
echo "   Connection will be available at: ${PROXY_ADDRESS}"
echo ""

# Run the proxy with proper error handling
cloud-sql-proxy \
    --address 0.0.0.0 \
    --port ${LOCAL_PORT} \
    ${INSTANCE_CONNECTION_NAME} || {
    echo ""
    echo "❌ Failed to start Cloud SQL Auth Proxy"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "   1. Ensure you're authenticated with Google Cloud:"
    echo "      gcloud auth application-default login"
    echo ""
    echo "   2. Verify the instance connection name:"
    echo "      gcloud sql instances list"
    echo ""
    echo "   3. Check your permissions:"
    echo "      gcloud projects get-iam-policy avisk-ai-platform"
    echo ""
    exit 1
}

echo ""
echo "👋 Cloud SQL Auth Proxy stopped"