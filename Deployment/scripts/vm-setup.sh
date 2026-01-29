#!/bin/bash

# VM Initial Setup Script for Avisk Core Services
# This script sets up a fresh Google Cloud VM for running the application

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check arguments
if [ "$#" -lt 2 ]; then
    print_error "Usage: $0 <PROJECT_ID> <ZONE> [VM_NAME]"
    echo "Example: $0 my-project us-central1-a avisk-core-services-vm1"
    exit 1
fi

PROJECT_ID=$1
ZONE=$2
VM_NAME=${3:-avisk-core-services-vm1}

print_info "Starting VM setup for $VM_NAME in project $PROJECT_ID (zone: $ZONE)"

# Set project
gcloud config set project "$PROJECT_ID"

# Create setup script to run on VM
SETUP_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e

echo "=================================="
echo "VM Setup for Avisk Core Services"
echo "=================================="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    build-essential \
    gcc \
    g++ \
    unixodbc-dev \
    nginx \
    supervisor \
    htop \
    net-tools

# Verify Python installation
python3 --version
pip3 --version

# Create application user
echo "Creating application user..."
if ! id -u avisk >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash avisk
    echo "User 'avisk' created"
else
    echo "User 'avisk' already exists"
fi

# Create directory structure
echo "Creating directory structure..."
sudo mkdir -p /opt/avisk/{app,logs,config,backups,venv}
sudo chown -R avisk:avisk /opt/avisk

# Create virtual environment
echo "Creating Python virtual environment..."
sudo -u avisk python3 -m venv /opt/avisk/venv

# Upgrade pip in virtual environment
sudo -u avisk /opt/avisk/venv/bin/pip install --upgrade pip setuptools wheel

# Create environment configuration file
echo "Creating environment configuration..."
sudo -u avisk tee /opt/avisk/config/.env > /dev/null <<ENVFILE
# Avisk Core Services Environment Configuration
DEPLOYMENT_ENV=production
ENVIRONMENT=production

# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Python Settings
PYTHONPATH=/opt/avisk/app

# Database Configuration (Update these values)
DB_PASSWORD=CHANGE_ME
DB_HOST=localhost
DB_NAME=avisk_db
DB_USER=avisk_user

# Google Cloud Storage
USE_GCS=true
GCS_BUCKET_NAME=avisk-app-data-eb7773c8

# Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/avisk/logs/application.log
ENVFILE

# Create Streamlit config
echo "Creating Streamlit configuration..."
sudo -u avisk mkdir -p /opt/avisk/config/.streamlit
sudo -u avisk tee /opt/avisk/config/.streamlit/config.toml > /dev/null <<STREAMLITCONFIG
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false
serverAddress = "0.0.0.0"
serverPort = 8501

[runner]
fastReruns = true
magicEnabled = true

[logger]
level = "info"

[theme]
base = "light"
STREAMLITCONFIG

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/avisk-core-services.service > /dev/null <<SYSTEMDSERVICE
[Unit]
Description=Avisk Core Services - Streamlit Application
After=network.target

[Service]
Type=simple
User=avisk
Group=avisk
WorkingDirectory=/opt/avisk/app
EnvironmentFile=/opt/avisk/config/.env
Environment="PATH=/opt/avisk/venv/bin:/usr/local/bin:/usr/bin:/bin"

ExecStart=/opt/avisk/venv/bin/streamlit run main.py \\
    --server.port=8501 \\
    --server.address=0.0.0.0 \\
    --server.headless=true

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=avisk-core-services

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SYSTEMDSERVICE

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Create log rotation config
echo "Configuring log rotation..."
sudo tee /etc/logrotate.d/avisk-core-services > /dev/null <<LOGROTATE
/opt/avisk/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 avisk avisk
    sharedscripts
    postrotate
        systemctl reload avisk-core-services > /dev/null 2>&1 || true
    endscript
}
LOGROTATE

# Configure firewall (if ufw is installed)
if command -v ufw &> /dev/null; then
    echo "Configuring firewall..."
    sudo ufw allow 8501/tcp comment 'Streamlit Application'
    echo "Firewall rule added for port 8501"
fi

# Create deployment info file
sudo -u avisk tee /opt/avisk/deployment-info.txt > /dev/null <<DEPLOYINFO
VM Setup completed on: $(date)
VM Name: $(hostname)
Python Version: $(python3 --version)
VM Setup Script Version: 1.0
DEPLOYINFO

echo "=================================="
echo "✅ VM Setup Complete!"
echo "=================================="
echo ""
echo "Next Steps:"
echo "1. Update environment variables in /opt/avisk/config/.env"
echo "2. Deploy application code using vm-deploy.sh script"
echo "3. Start the service: sudo systemctl start avisk-core-services"
echo ""
echo "Useful Commands:"
echo "  - Check service status: sudo systemctl status avisk-core-services"
echo "  - View logs: sudo journalctl -u avisk-core-services -f"
echo "  - Restart service: sudo systemctl restart avisk-core-services"
echo ""
EOF
)

# Copy setup script to VM and execute
print_info "Uploading setup script to VM..."
echo "$SETUP_SCRIPT" | gcloud compute ssh "$VM_NAME" \
    --zone="$ZONE" \
    --command="cat > /tmp/vm-setup.sh && chmod +x /tmp/vm-setup.sh && bash /tmp/vm-setup.sh"

if [ $? -eq 0 ]; then
    print_info "VM setup completed successfully!"
    echo ""
    print_info "Next steps:"
    echo "  1. Deploy application: ./Deployment/scripts/vm-deploy.sh $PROJECT_ID $ZONE"
    echo "  2. Configure environment: gcloud compute ssh $VM_NAME --zone=$ZONE"
    echo "     Edit: /opt/avisk/config/.env"
    echo ""
else
    print_error "VM setup failed. Please check the logs above."
    exit 1
fi

# Configure Google Cloud firewall rule
print_info "Checking firewall rules..."
if ! gcloud compute firewall-rules describe allow-streamlit-8501 --project="$PROJECT_ID" &>/dev/null; then
    print_warning "Creating firewall rule for port 8501..."
    gcloud compute firewall-rules create allow-streamlit-8501 \
        --project="$PROJECT_ID" \
        --allow=tcp:8501 \
        --source-ranges=0.0.0.0/0 \
        --description="Allow Streamlit traffic to Avisk Core Services" \
        --direction=INGRESS
    
    print_info "Firewall rule created successfully"
else
    print_info "Firewall rule already exists"
fi

# Get VM external IP
print_info "Getting VM external IP..."
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
print_info "VM Setup Summary:"
echo "  VM Name: $VM_NAME"
echo "  Zone: $ZONE"
echo "  External IP: $EXTERNAL_IP"
echo "  Application URL (after deployment): http://$EXTERNAL_IP:8501"
echo ""
print_warning "Remember to configure environment variables before deploying the application!"
