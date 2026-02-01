#!/bin/bash

# Cloud SQL Proxy Setup Script for VM
# This script installs and configures Cloud SQL Proxy to enable database connections

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running with required arguments
if [ "$#" -lt 3 ]; then
    print_error "Usage: $0 <PROJECT_ID> <ZONE> <VM_NAME> [INSTANCE_CONNECTION_NAME]"
    echo "Example: $0 avisk-ai-platform us-central1-a avisk-core-services-vm1 avisk-ai-platform:us-central1:avisk-core-dev"
    exit 1
fi

PROJECT_ID=$1
ZONE=$2
VM_NAME=$3
INSTANCE_CONNECTION_NAME=${4:-avisk-ai-platform:us-central1:avisk-core-dev}

print_info "Setting up Cloud SQL Proxy on $VM_NAME"
print_info "Instance: $INSTANCE_CONNECTION_NAME"

# Set project
gcloud config set project "$PROJECT_ID"

print_step "1/4 Installing Cloud SQL Auth Proxy..."

# Create setup script for VM
SETUP_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

echo "Installing Cloud SQL Auth Proxy..."

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    PROXY_URL="https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    PROXY_URL="https://dl.google.com/cloudsql/cloud_sql_proxy.linux.arm64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

echo "Detected architecture: $ARCH"
echo "Downloading from: $PROXY_URL"

# Download Cloud SQL Auth Proxy
cd /tmp
wget "$PROXY_URL" -O cloud_sql_proxy
chmod +x cloud_sql_proxy
sudo mv cloud_sql_proxy /usr/local/bin/

# Verify installation
cloud_sql_proxy --version

echo "✅ Cloud SQL Auth Proxy installed successfully"
EOF
)

# Execute setup on VM
echo "$SETUP_SCRIPT" | gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="bash -s"

print_step "2/4 Creating Cloud SQL Proxy systemd service..."

# Create systemd service file
SERVICE_FILE=$(cat <<EOF
[Unit]
Description=Cloud SQL Auth Proxy
After=network.target
Requires=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/tmp
ExecStart=/usr/local/bin/cloud_sql_proxy \\
    --unix-socket=/cloudsql \\
    $INSTANCE_CONNECTION_NAME
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
)

# Create the service file on VM
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="sudo bash -c 'echo \"$SERVICE_FILE\" > /etc/systemd/system/cloud-sql-proxy.service'"

print_step "3/4 Creating /cloudsql directory..."

gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="sudo mkdir -p /cloudsql && sudo chmod 755 /cloudsql"

print_step "4/4 Starting Cloud SQL Proxy service..."

# Start and enable the service
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
    sudo systemctl daemon-reload
    sudo systemctl enable cloud-sql-proxy
    sudo systemctl start cloud-sql-proxy
    sleep 3
    sudo systemctl status cloud-sql-proxy --no-pager
"

print_info "Verifying Cloud SQL Proxy socket..."

gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command="
    sleep 2
    if [ -S /cloudsql/$INSTANCE_CONNECTION_NAME/.s.PGSQL.5432 ]; then
        echo '✅ Cloud SQL Proxy socket is ready'
        ls -la /cloudsql/$INSTANCE_CONNECTION_NAME/
    else
        echo '⚠️  Socket not found yet, checking logs...'
        sudo journalctl -u cloud-sql-proxy -n 20 --no-pager
    fi
"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Cloud SQL Proxy Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Useful Commands:"
echo "  - Check status: gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo systemctl status cloud-sql-proxy"
echo "  - View logs: gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo journalctl -u cloud-sql-proxy -f"
echo "  - Restart proxy: gcloud compute ssh $VM_NAME --zone=$ZONE -- sudo systemctl restart cloud-sql-proxy"
echo ""
