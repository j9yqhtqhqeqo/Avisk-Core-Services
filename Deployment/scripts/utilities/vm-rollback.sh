#!/bin/bash

# VM Rollback Script for Avisk Core Services
# This script rolls back to a previous deployment backup

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check arguments
if [ "$#" -lt 2 ]; then
    print_error "Usage: $0 <PROJECT_ID> <ZONE> [VM_NAME] [BACKUP_FILE]"
    echo ""
    echo "If BACKUP_FILE is not specified, the script will show available backups"
    echo ""
    echo "Example:"
    echo "  $0 my-project us-central1-a                                    # List backups"
    echo "  $0 my-project us-central1-a avisk-core-services-vm1 app-backup-20260129120000.tar.gz"
    exit 1
fi

PROJECT_ID=$1
ZONE=$2
VM_NAME=${3:-avisk-core-services-vm1}
BACKUP_FILE=$4

print_info "Connecting to $VM_NAME..."

# Create rollback script
ROLLBACK_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

BACKUP_FILE=$1

echo "=========================================="
echo "Avisk Core Services - Rollback"
echo "=========================================="

# List available backups if no file specified
if [ -z "$BACKUP_FILE" ]; then
    echo ""
    echo "Available backups:"
    echo ""
    if [ -d "/opt/avisk/backups" ] && [ "$(ls -A /opt/avisk/backups/*.tar.gz 2>/dev/null)" ]; then
        ls -lh /opt/avisk/backups/*.tar.gz | awk '{print "  " $9 " (" $5 ", " $6 " " $7 " " $8 ")"}'
        echo ""
        echo "To rollback, run this script with the backup filename:"
        echo "  Example: vm-rollback.sh <PROJECT> <ZONE> <VM> app-backup-20260129120000.tar.gz"
    else
        echo "  No backups found in /opt/avisk/backups/"
    fi
    echo ""
    exit 0
fi

# Verify backup exists
if [ ! -f "/opt/avisk/backups/$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: /opt/avisk/backups/$BACKUP_FILE"
    exit 1
fi

echo ""
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to rollback? This will replace the current deployment. (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo "Starting rollback..."

# Stop service
echo "Stopping service..."
sudo systemctl stop avisk-core-services

# Create backup of current state
echo "Backing up current state..."
sudo tar -czf "/opt/avisk/backups/pre-rollback-$(date +%Y%m%d%H%M%S).tar.gz" \
    -C /opt/avisk app/ 2>/dev/null || true

# Remove current deployment
echo "Removing current deployment..."
sudo rm -rf /opt/avisk/app/*

# Extract backup
echo "Restoring backup..."
sudo tar -xzf "/opt/avisk/backups/$BACKUP_FILE" -C /

# Set ownership
sudo chown -R avisk:avisk /opt/avisk/app

# Start service
echo "Starting service..."
sudo systemctl start avisk-core-services

# Wait and check status
sleep 5

if sudo systemctl is-active --quiet avisk-core-services; then
    echo ""
    echo "=========================================="
    echo "✅ Rollback Successful!"
    echo "=========================================="
    echo "Service Status: RUNNING"
    echo "Restored from: $BACKUP_FILE"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ Rollback Failed!"
    echo "=========================================="
    echo "Service failed to start. Check logs:"
    sudo journalctl -u avisk-core-services -n 50 --no-pager
    exit 1
fi
EOF
)

# Execute rollback script on VM
echo "$ROLLBACK_SCRIPT" | gcloud compute ssh "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="bash -s -- $BACKUP_FILE"

if [ $? -eq 0 ] && [ -n "$BACKUP_FILE" ]; then
    echo ""
    print_info "Rollback completed. Verify the application is working correctly."
    
    # Get VM external IP
    EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
    
    echo "  Application URL: http://$EXTERNAL_IP:8501"
fi
