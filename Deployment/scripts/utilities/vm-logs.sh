#!/bin/bash

# VM Logs Viewer Script for Avisk Core Services
# This script provides easy access to application logs

set -e

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Check arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <PROJECT_ID> <ZONE> [VM_NAME] [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --follow       Follow log output (like tail -f)"
    echo "  -n, --lines NUM    Show NUM lines (default: 50)"
    echo "  -s, --since TIME   Show logs since TIME (e.g., '1 hour ago', '2024-01-29 10:00')"
    echo ""
    echo "Examples:"
    echo "  $0 my-project us-central1-a                     # Show last 50 lines"
    echo "  $0 my-project us-central1-a -f                  # Follow logs in real-time"
    echo "  $0 my-project us-central1-a -n 100              # Show last 100 lines"
    echo "  $0 my-project us-central1-a -s '1 hour ago'     # Show logs from last hour"
    exit 1
fi

PROJECT_ID=$1
ZONE=$2
VM_NAME=${3:-avisk-core-services-vm1}

# Parse optional flags
shift 2
[ $# -gt 0 ] && shift

FOLLOW=""
LINES=50
SINCE=""

while [ $# -gt 0 ]; do
    case $1 in
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n|--lines)
            LINES=$2
            shift 2
            ;;
        -s|--since)
            SINCE="--since \"$2\""
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Build journalctl command
if [ -n "$SINCE" ]; then
    CMD="sudo journalctl -u avisk-core-services $SINCE $FOLLOW"
elif [ -n "$FOLLOW" ]; then
    CMD="sudo journalctl -u avisk-core-services -f"
else
    CMD="sudo journalctl -u avisk-core-services -n $LINES --no-pager"
fi

print_info "Connecting to $VM_NAME to view logs..."
echo -e "${BLUE}Command: $CMD${NC}"
echo ""

# Execute log command on VM
gcloud compute ssh "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$CMD"
