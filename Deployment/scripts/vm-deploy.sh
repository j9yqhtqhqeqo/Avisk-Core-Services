#!/bin/bash

# VM Deployment Script for Avisk Core Services
# This script deploys the application to a Google Cloud VM

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check arguments
if [ "$#" -lt 2 ]; then
    print_error "Usage: $0 <PROJECT_ID> <ZONE> [VM_NAME]"
    echo "Example: $0 my-project us-central1-a avisk-core-services-vm1"
    exit 1
fi

PROJECT_ID=$1
ZONE=$2
VM_NAME=${3:-avisk-core-services-vm1}
DEPLOY_DIR=$(mktemp -d)
BUILD_ID=$(date +%Y%m%d%H%M%S)

print_info "Starting deployment to $VM_NAME in project $PROJECT_ID (zone: $ZONE)"
print_info "Build ID: $BUILD_ID"

# Set project
gcloud config set project "$PROJECT_ID"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

print_step "1/6 Creating deployment package..."

# Create deployment package
cd "$PROJECT_ROOT"

# List of directories to include
INCLUDE_DIRS=(
    "AI"
    "AviskUIAPI"
    "Clients"
    "Dashboards"
    "DBEntities"
    "Dictionary"
    "ESGInsights"
    "pages"
    "Services"
    "Utilities"
)

# List of files to include
INCLUDE_FILES=(
    "main.py"
    "health.py"
    "version.py"
    "__init__.py"
    "Deployment/requirements.txt"
)

# Create deployment directory
mkdir -p "$DEPLOY_DIR/app"

# Copy directories
for dir in "${INCLUDE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        print_info "Copying directory: $dir"
        cp -r "$dir" "$DEPLOY_DIR/app/"
    else
        print_warning "Directory not found: $dir"
    fi
done

# Copy files
for file in "${INCLUDE_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_info "Copying file: $file"
        cp "$file" "$DEPLOY_DIR/app/"
    else
        print_warning "File not found: $file"
    fi
done

# Copy requirements.txt to root of deploy dir
cp Deployment/requirements.txt "$DEPLOY_DIR/requirements.txt"

# Create deployment metadata
cat > "$DEPLOY_DIR/deployment-metadata.json" <<EOF
{
    "build_id": "$BUILD_ID",
    "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "deployed_by": "$(whoami)",
    "project_id": "$PROJECT_ID",
    "vm_name": "$VM_NAME",
    "zone": "$ZONE"
}
EOF

# Clean up Python cache files
find "$DEPLOY_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$DEPLOY_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$DEPLOY_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$DEPLOY_DIR" -type f -name "*.pyd" -delete 2>/dev/null || true
find "$DEPLOY_DIR" -type f -name ".DS_Store" -delete 2>/dev/null || true

# Create deployment archive
cd "$DEPLOY_DIR"
print_info "Creating deployment archive..."
tar -czf deployment.tar.gz app/ requirements.txt deployment-metadata.json

print_step "2/6 Uploading deployment package to VM..."

# Upload deployment package
gcloud compute scp deployment.tar.gz "$VM_NAME:/tmp/deployment-$BUILD_ID.tar.gz" \
    --zone="$ZONE" \
    --project="$PROJECT_ID"

print_step "3/6 Extracting and installing on VM..."

# Create deployment script to run on VM
DEPLOY_SCRIPT=$(cat <<'EOFSCRIPT'
#!/bin/bash
set -e

BUILD_ID=$1
echo "=================================="
echo "Avisk Core Services Deployment"
echo "Build ID: $BUILD_ID"
echo "=================================="

# Stop the service if running
echo "Stopping service..."
sudo systemctl stop avisk-core-services || true

# Backup current deployment
if [ -d "/opt/avisk/app" ]; then
    echo "Backing up current deployment..."
    sudo -u avisk mkdir -p /opt/avisk/backups
    sudo tar -czf "/opt/avisk/backups/app-backup-$(date +%Y%m%d%H%M%S).tar.gz" \
        -C /opt/avisk app/ 2>/dev/null || echo "No previous deployment to backup"
    
    # Keep only last 5 backups
    cd /opt/avisk/backups
    ls -t app-backup-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r sudo rm -f
fi

# Extract new deployment
echo "Extracting deployment package..."
cd /tmp
tar -xzf "deployment-$BUILD_ID.tar.gz"

# Remove old application directory
echo "Removing old application..."
sudo rm -rf /opt/avisk/app/*

# Copy new application
echo "Installing new application..."
sudo cp -r app/* /opt/avisk/app/
sudo cp deployment-metadata.json /opt/avisk/deployment-metadata.json

# Set ownership
sudo chown -R avisk:avisk /opt/avisk/app
sudo chown avisk:avisk /opt/avisk/deployment-metadata.json

# Install/update Python dependencies
echo "Installing Python dependencies..."
sudo -u avisk /opt/avisk/venv/bin/pip install --upgrade pip
sudo -u avisk /opt/avisk/venv/bin/pip install -r requirements.txt

# Clean up
rm -rf /tmp/deployment-$BUILD_ID.tar.gz /tmp/app /tmp/requirements.txt /tmp/deployment-metadata.json

# Start the service
echo "Starting service..."
sudo systemctl start avisk-core-services

# Wait for service to start
echo "Waiting for service to start..."
sleep 5

# Check service status
if sudo systemctl is-active --quiet avisk-core-services; then
    echo "=================================="
    echo "✅ Deployment Successful!"
    echo "=================================="
    echo "Service Status: RUNNING"
    echo "Build ID: $BUILD_ID"
    echo ""
    echo "View logs: sudo journalctl -u avisk-core-services -f"
    echo ""
    exit 0
else
    echo "=================================="
    echo "❌ Deployment Failed!"
    echo "=================================="
    echo "Service failed to start. Checking logs..."
    sudo journalctl -u avisk-core-services -n 50 --no-pager
    exit 1
fi
EOFSCRIPT
)

# Execute deployment script on VM
print_info "Running deployment script on VM..."
echo "$DEPLOY_SCRIPT" | gcloud compute ssh "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="cat > /tmp/deploy.sh && chmod +x /tmp/deploy.sh && bash /tmp/deploy.sh $BUILD_ID"

DEPLOY_RESULT=$?

print_step "4/6 Verifying deployment..."

if [ $DEPLOY_RESULT -eq 0 ]; then
    # Verify service is running
    print_info "Checking service status..."
    gcloud compute ssh "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --command="sudo systemctl is-active avisk-core-services"
    
    print_step "5/6 Testing application health..."
    
    # Get VM external IP
    EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    
    # Wait for application to be ready
    print_info "Waiting for application to be ready..."
    sleep 10
    
    # Test health endpoint (optional, may not work if firewall not configured)
    if curl -f -s --max-time 5 "http://$EXTERNAL_IP:8501" > /dev/null 2>&1; then
        print_info "Application is responding to HTTP requests"
    else
        print_warning "Could not verify HTTP endpoint (firewall may not be configured)"
    fi
    
    print_step "6/6 Cleaning up..."
    
    # Clean up local temp directory
    rm -rf "$DEPLOY_DIR"
    
    echo ""
    echo "=========================================="
    print_info "🎉 Deployment Completed Successfully!"
    echo "=========================================="
    echo ""
    echo "Deployment Details:"
    echo "  Build ID: $BUILD_ID"
    echo "  VM Name: $VM_NAME"
    echo "  Zone: $ZONE"
    echo "  External IP: $EXTERNAL_IP"
    echo "  Application URL: http://$EXTERNAL_IP:8501"
    echo ""
    echo "Useful Commands:"
    echo "  - View logs: gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo journalctl -u avisk-core-services -f"
    echo "  - Check status: gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo systemctl status avisk-core-services"
    echo "  - Restart service: gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo systemctl restart avisk-core-services"
    echo ""
else
    print_error "Deployment failed. Please check the logs above."
    rm -rf "$DEPLOY_DIR"
    exit 1
fi
