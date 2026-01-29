# VM Deployment Guide for Avisk Core Services

This guide explains how to deploy the Avisk Core Services application to a Google Cloud VM instance.

## VM Details

- **VM Name**: avisk-core-services-vm1
- **Deployment Type**: Direct deployment (non-containerized)
- **Application Type**: Streamlit-based web application
- **Port**: 8501 (Streamlit default)

## Prerequisites

1. **Google Cloud SDK**: Install and authenticate
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Authenticate
   gcloud auth login
   ```

2. **SSH Access**: Ensure you can SSH to the VM
   ```bash
   gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>
   ```

3. **VM Requirements**:
   - Ubuntu 20.04 or later
   - Python 3.9 or higher
   - Minimum 2 vCPUs, 4GB RAM
   - Sufficient disk space (20GB+ recommended)

## Deployment Steps

### Step 1: Initial VM Setup (One-time)

Set up the VM environment with required dependencies:

```bash
# Run from your local machine
./Deployment/scripts/vm-setup.sh <PROJECT_ID> <ZONE>
```

This script will:
- Install Python 3.9, pip, and system dependencies
- Install required Python packages
- Set up the application directory structure
- Configure environment variables
- Create a systemd service for auto-start
- Configure firewall rules

### Step 2: Deploy Application Code

Deploy the application code to the VM:

```bash
# Run from your local machine
./Deployment/scripts/vm-deploy.sh <PROJECT_ID> <ZONE>
```

This script will:
- Create a deployment package
- Upload code to the VM
- Install/update dependencies
- Restart the application service
- Verify deployment health

### Step 3: Verify Deployment

Check the deployment status:

```bash
# Run from your local machine
./Deployment/scripts/vm-verify.sh <PROJECT_ID> <ZONE>
```

Or manually verify:
```bash
# SSH to the VM
gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Check service status
sudo systemctl status avisk-core-services

# View application logs
sudo journalctl -u avisk-core-services -f
```

## Application Management

### Start/Stop/Restart Service

```bash
# SSH to the VM first
gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Start the service
sudo systemctl start avisk-core-services

# Stop the service
sudo systemctl stop avisk-core-services

# Restart the service
sudo systemctl restart avisk-core-services

# View status
sudo systemctl status avisk-core-services
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u avisk-core-services -f

# Last 100 lines
sudo journalctl -u avisk-core-services -n 100

# Logs from specific time
sudo journalctl -u avisk-core-services --since "1 hour ago"
```

### Update Application

To update the application with new code:

```bash
# From your local machine
./Deployment/scripts/vm-deploy.sh <PROJECT_ID> <ZONE>
```

## Environment Configuration

### Environment Variables

Environment variables are stored in `/opt/avisk/config/.env` on the VM.

To update environment variables:

```bash
# SSH to VM
gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Edit environment file
sudo nano /opt/avisk/config/.env

# Restart service to apply changes
sudo systemctl restart avisk-core-services
```

### Database Configuration

Set database credentials in the environment file:

```env
DB_PASSWORD=your_password
ENVIRONMENT=production
DB_HOST=your_db_host
DB_NAME=your_db_name
DB_USER=your_db_user
```

### Google Cloud Storage

Configure GCS access:

```env
USE_GCS=true
GCS_BUCKET_NAME=avisk-app-data-eb7773c8
GOOGLE_APPLICATION_CREDENTIALS=/opt/avisk/config/gcs-credentials.json
```

## Firewall Configuration

Ensure the VM allows traffic on port 8501:

```bash
# Create firewall rule (run once)
gcloud compute firewall-rules create allow-streamlit \
    --allow=tcp:8501 \
    --source-ranges=0.0.0.0/0 \
    --description="Allow Streamlit traffic"

# Or restrict to specific IP ranges
gcloud compute firewall-rules create allow-streamlit \
    --allow=tcp:8501 \
    --source-ranges=YOUR_IP_RANGE \
    --description="Allow Streamlit traffic from specific IPs"
```

## Accessing the Application

### Public Access

After deployment, access the application at:

```
http://<VM_EXTERNAL_IP>:8501
```

Get the external IP:
```bash
gcloud compute instances describe avisk-core-services-vm1 \
    --zone=<YOUR_ZONE> \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### SSH Tunnel (Recommended for Development)

For secure access during development:

```bash
# Create SSH tunnel
gcloud compute ssh avisk-core-services-vm1 \
    --zone=<YOUR_ZONE> \
    -- -L 8501:localhost:8501

# Access via browser
open http://localhost:8501
```

## Monitoring and Troubleshooting

### Check Service Health

```bash
# SSH to VM
gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Check if service is running
sudo systemctl is-active avisk-core-services

# Check if service is enabled
sudo systemctl is-enabled avisk-core-services

# View detailed status
sudo systemctl status avisk-core-services
```

### Common Issues

#### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u avisk-core-services -n 50

# Check Python path
which python3

# Verify dependencies
pip3 list
```

#### Port Already in Use

```bash
# Find process using port 8501
sudo lsof -i :8501

# Kill process if needed
sudo kill -9 <PID>

# Restart service
sudo systemctl restart avisk-core-services
```

#### Permission Issues

```bash
# Fix ownership
sudo chown -R avisk:avisk /opt/avisk

# Fix permissions
sudo chmod -R 755 /opt/avisk/app
```

## Backup and Recovery

### Backup Application Data

```bash
# SSH to VM
gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Create backup
sudo tar -czf /opt/avisk/backups/app-backup-$(date +%Y%m%d).tar.gz \
    /opt/avisk/app /opt/avisk/config

# Download backup to local machine
gcloud compute scp avisk-core-services-vm1:/opt/avisk/backups/app-backup-*.tar.gz . \
    --zone=<YOUR_ZONE>
```

### Restore from Backup

```bash
# Upload backup to VM
gcloud compute scp app-backup-*.tar.gz avisk-core-services-vm1:/tmp/ \
    --zone=<YOUR_ZONE>

# SSH to VM
gcloud compute ssh avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Stop service
sudo systemctl stop avisk-core-services

# Restore backup
sudo tar -xzf /tmp/app-backup-*.tar.gz -C /

# Start service
sudo systemctl start avisk-core-services
```

## Performance Tuning

### Increase VM Resources

```bash
# Stop VM
gcloud compute instances stop avisk-core-services-vm1 --zone=<YOUR_ZONE>

# Change machine type
gcloud compute instances set-machine-type avisk-core-services-vm1 \
    --machine-type=n1-standard-2 \
    --zone=<YOUR_ZONE>

# Start VM
gcloud compute instances start avisk-core-services-vm1 --zone=<YOUR_ZONE>
```

### Optimize Streamlit

Edit `/opt/avisk/config/streamlit_config.toml`:

```toml
[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false

[runner]
fastReruns = true
```

## Security Best Practices

1. **Restrict Firewall Rules**: Limit access to specific IP ranges
2. **Use SSH Keys**: Disable password authentication
3. **Regular Updates**: Keep system packages updated
4. **Service Account**: Use minimal permissions for GCS access
5. **Environment Variables**: Never commit credentials to version control
6. **HTTPS**: Consider setting up a reverse proxy with SSL (nginx + Let's Encrypt)

## Migration from Cloud Run

Key differences from Cloud Run deployment:

| Aspect | Cloud Run | VM Deployment |
|--------|-----------|---------------|
| Scaling | Automatic | Manual/Pre-configured |
| Cost | Pay per request | Fixed VM cost |
| Startup Time | Cold starts | Always running |
| Management | Fully managed | Self-managed |
| Port | 8080 | 8501 |
| Health Check | HTTP endpoint | systemd |

## Support

For issues or questions:
1. Check application logs: `sudo journalctl -u avisk-core-services -f`
2. Verify service status: `sudo systemctl status avisk-core-services`
3. Check VM resources: `top`, `df -h`, `free -m`
4. Review firewall rules: `gcloud compute firewall-rules list`
