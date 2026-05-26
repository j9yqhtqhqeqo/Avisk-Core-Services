#!/bin/bash

# VM Verification Script for Avisk Core Services
# This script verifies the deployment and health of the application

set -e

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

print_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

print_fail() {
    echo -e "${RED}✗${NC} $1"
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

echo "=========================================="
echo "Avisk Core Services - Deployment Verification"
echo "=========================================="
echo ""

# Set project
gcloud config set project "$PROJECT_ID" > /dev/null 2>&1

print_info "Verifying deployment for $VM_NAME..."
echo ""

# Check if VM exists and is running
print_info "Checking VM status..."
VM_STATUS=$(gcloud compute instances describe "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --format='get(status)' 2>/dev/null || echo "NOT_FOUND")

if [ "$VM_STATUS" = "RUNNING" ]; then
    print_ok "VM is running"
else
    print_fail "VM is not running (Status: $VM_STATUS)"
    exit 1
fi

# Get VM external IP
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

print_info "VM External IP: $EXTERNAL_IP"
echo ""

# Create verification script to run on VM
VERIFY_SCRIPT=$(cat <<'EOF'
#!/bin/bash

echo "Running system checks..."
echo ""

# Check service status
echo "1. Service Status:"
if sudo systemctl is-active --quiet avisk-core-services; then
    echo "   ✓ Service is ACTIVE"
    SERVICE_STATUS=0
else
    echo "   ✗ Service is NOT ACTIVE"
    sudo systemctl status avisk-core-services --no-pager -l
    SERVICE_STATUS=1
fi

# Check if service is enabled
if sudo systemctl is-enabled --quiet avisk-core-services; then
    echo "   ✓ Service is ENABLED (auto-start on boot)"
else
    echo "   ✗ Service is NOT ENABLED"
fi

echo ""

# Check process
echo "2. Application Process:"
if pgrep -f "streamlit run main.py" > /dev/null; then
    PID=$(pgrep -f "streamlit run main.py")
    echo "   ✓ Application is running (PID: $PID)"
    
    # Get memory usage
    MEM=$(ps -p $PID -o %mem --no-headers | xargs)
    echo "   Memory Usage: ${MEM}%"
    
    # Get CPU usage
    CPU=$(ps -p $PID -o %cpu --no-headers | xargs)
    echo "   CPU Usage: ${CPU}%"
else
    echo "   ✗ Application process not found"
fi

echo ""

# Check port
echo "3. Port Status:"
if sudo netstat -tulpn 2>/dev/null | grep -q ":8501"; then
    echo "   ✓ Port 8501 is listening"
    sudo netstat -tulpn | grep ":8501"
else
    echo "   ✗ Port 8501 is not listening"
fi

echo ""

# Check application files
echo "4. Application Files:"
if [ -d "/opt/avisk/app" ]; then
    echo "   ✓ Application directory exists"
    FILE_COUNT=$(find /opt/avisk/app -name "*.py" | wc -l)
    echo "   Python files: $FILE_COUNT"
else
    echo "   ✗ Application directory not found"
fi

if [ -f "/opt/avisk/app/main.py" ]; then
    echo "   ✓ main.py exists"
else
    echo "   ✗ main.py not found"
fi

echo ""

# Check deployment metadata
echo "5. Deployment Information:"
if [ -f "/opt/avisk/deployment-metadata.json" ]; then
    echo "   ✓ Deployment metadata found"
    cat /opt/avisk/deployment-metadata.json | python3 -m json.tool
else
    echo "   ✗ Deployment metadata not found"
fi

echo ""

# Check logs
echo "6. Recent Logs (last 20 lines):"
sudo journalctl -u avisk-core-services -n 20 --no-pager

echo ""

# Check disk space
echo "7. Disk Usage:"
df -h /opt/avisk | tail -n 1

echo ""

# Check virtual environment
echo "8. Python Environment:"
if [ -d "/opt/avisk/venv" ]; then
    echo "   ✓ Virtual environment exists"
    PACKAGE_COUNT=$(/opt/avisk/venv/bin/pip list 2>/dev/null | wc -l)
    echo "   Installed packages: $((PACKAGE_COUNT - 2))"
else
    echo "   ✗ Virtual environment not found"
fi

echo ""

# Return service status
exit $SERVICE_STATUS
EOF
)

# Execute verification script on VM
print_info "Running verification checks on VM..."
echo ""

gcloud compute ssh "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="bash -s" <<< "$VERIFY_SCRIPT"

VERIFY_RESULT=$?

echo ""
echo "=========================================="

if [ $VERIFY_RESULT -eq 0 ]; then
    print_ok "All checks passed!"
    echo ""
    echo "Application Access:"
    echo "  URL: http://$EXTERNAL_IP:8501"
    echo ""
    echo "SSH Access:"
    echo "  gcloud compute ssh $VM_NAME --zone=$ZONE"
    echo ""
    echo "Log Monitoring:"
    echo "  gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo journalctl -u avisk-core-services -f"
    echo ""
else
    print_fail "Some checks failed. Please review the output above."
    echo ""
    echo "Troubleshooting Commands:"
    echo "  - SSH to VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
    echo "  - View logs: sudo journalctl -u avisk-core-services -f"
    echo "  - Restart service: sudo systemctl restart avisk-core-services"
    echo "  - Check status: sudo systemctl status avisk-core-services"
    echo ""
    exit 1
fi

echo "=========================================="
