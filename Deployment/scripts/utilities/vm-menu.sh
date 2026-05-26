#!/bin/bash

# Example Usage Script for VM Deployment
# This file shows how to use the deployment scripts

# Replace these with your actual values
PROJECT_ID="avisk-ai-platform"
ZONE="us-central1-a"
VM_NAME="avisk-core-services-vm1"

echo "======================================"
echo "Avisk Core Services - VM Deployment"
echo "======================================"
echo ""
echo "⚠️  IMPORTANT: Update the variables at the top of this script!"
echo ""
echo "PROJECT_ID: $PROJECT_ID"
echo "ZONE: $ZONE"
echo "VM_NAME: $VM_NAME"
echo ""

# Check if variables are updated
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo "❌ ERROR: Please update PROJECT_ID in this script"
    exit 1
fi

# Menu
echo "Select an option:"
echo ""
echo "  1) First-time setup (run once)"
echo "  2) Deploy application"
echo "  3) Verify deployment"
echo "  4) View logs (follow mode)"
echo "  5) View last 100 log lines"
echo "  6) Check service status"
echo "  7) Restart service"
echo "  8) List backups / Rollback"
echo "  9) Get VM external IP"
echo "  0) SSH to VM"
echo ""
read -p "Enter choice [0-9]: " choice

case $choice in
    1)
        echo ""
        echo "Running first-time setup..."
        ./Deployment/scripts/vm-setup.sh "$PROJECT_ID" "$ZONE" "$VM_NAME"
        echo ""
        echo "Next steps:"
        echo "1. Configure environment: gcloud compute ssh $VM_NAME --zone=$ZONE"
        echo "   sudo nano /opt/avisk/config/.env"
        echo "2. Run option 2 to deploy the application"
        ;;
    2)
        echo ""
        echo "Deploying application..."
        ./Deployment/scripts/vm-deploy.sh "$PROJECT_ID" "$ZONE" "$VM_NAME"
        ;;
    3)
        echo ""
        echo "Verifying deployment..."
        ./Deployment/scripts/vm-verify.sh "$PROJECT_ID" "$ZONE" "$VM_NAME"
        ;;
    4)
        echo ""
        echo "Viewing logs (press Ctrl+C to exit)..."
        ./Deployment/scripts/vm-logs.sh "$PROJECT_ID" "$ZONE" "$VM_NAME" -f
        ;;
    5)
        echo ""
        echo "Last 100 log lines:"
        ./Deployment/scripts/vm-logs.sh "$PROJECT_ID" "$ZONE" "$VM_NAME" -n 100
        ;;
    6)
        echo ""
        echo "Checking service status..."
        gcloud compute ssh "$VM_NAME" --zone="$ZONE" \
            -- sudo systemctl status avisk-core-services
        ;;
    7)
        echo ""
        echo "Restarting service..."
        gcloud compute ssh "$VM_NAME" --zone="$ZONE" \
            -- sudo systemctl restart avisk-core-services
        echo "Service restarted. Use option 3 to verify."
        ;;
    8)
        echo ""
        echo "Managing backups..."
        ./Deployment/scripts/vm-rollback.sh "$PROJECT_ID" "$ZONE" "$VM_NAME"
        ;;
    9)
        echo ""
        echo "Getting VM external IP..."
        EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
            --zone="$ZONE" \
            --project="$PROJECT_ID" \
            --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
        echo ""
        echo "VM External IP: $EXTERNAL_IP"
        echo "Application URL: http://$EXTERNAL_IP:8501"
        echo ""
        ;;
    0)
        echo ""
        echo "Connecting to VM via SSH..."
        gcloud compute ssh "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Done!"
