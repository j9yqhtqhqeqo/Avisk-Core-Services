# Avisk Core Services Deployment Guide

This directory contains deployment configurations and scripts for deploying the Avisk Core Services application to Google Cloud Platform.

## 🚀 Deployment Options

### 1. Google Cloud VM (Recommended for Predictable Performance)

Deploy directly to a Google Cloud VM instance for predictable performance and full control.

**VM Name**: `avisk-core-services-vm1`

**Quick Start:**
```bash
# One-time setup
./scripts/vm-setup.sh YOUR_PROJECT_ID YOUR_ZONE

# Deploy application
./scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE
```

**Documentation:**
- [VM_QUICKSTART.md](VM_QUICKSTART.md) - Quick reference guide ⭐
- [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md) - Detailed VM deployment guide

---

### 2. Cloud Run (Recommended for Auto-Scaling)

Cloud Run provides automatic scaling, high availability, and pay-per-use pricing.

**Quick Start:**
```bash
# Deploy to Cloud Run
./scripts/deploy-cloudrun.sh YOUR_PROJECT_ID us-central1
```

**Documentation:**
- [CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md) - Detailed Cloud Run deployment guide

---

### 3. App Engine

App Engine offers a fully managed platform with automatic scaling.

**Quick Start:**
```bash
# Deploy to App Engine
gcloud app deploy app.yaml
```

---

## 📊 Deployment Comparison

| Feature | VM Deployment | Cloud Run |
|---------|---------------|-----------|
| **Scaling** | Manual | Automatic |
| **Cost** | Fixed (~$25-40/mo) | Variable ($5-50/mo) |
| **Cold Starts** | None ✓ | Possible |
| **Management** | Self-managed | Fully managed |
| **Port** | 8501 | 8080 |
| **Setup Time** | ~15 min | ~10 min |

See [DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md) for detailed comparison.

---

## 📁 Directory Structure

```
Deployment/
├── README.md                      # This file
├── VM_QUICKSTART.md              # VM quick start guide ⭐ NEW
├── VM_DEPLOYMENT.md              # VM deployment guide (NEW)
├── DEPLOYMENT_COMPARISON.md      # VM vs Cloud Run comparison (NEW)
├── CLOUD_RUN_DEPLOYMENT.md       # Cloud Run deployment guide
├── app.yaml                       # App Engine configuration
├── cloudbuild-cloudrun.yaml      # Cloud Build config for Cloud Run
├── cloudbuild.yaml               # General Cloud Build config
├── cloudrun-service.yaml         # Cloud Run service definition
├── requirements.txt              # Production dependencies
├── environments/                 # Environment-specific configs
│   ├── dev.env
│   ├── staging.env
│   └── production.env
└── scripts/                      # Deployment scripts
    ├── vm-setup.sh               # VM initial setup (NEW)
    ├── vm-deploy.sh              # Deploy to VM (NEW)
    ├── vm-verify.sh              # Verify VM deployment (NEW)
    ├── vm-logs.sh                # View VM logs (NEW)
    ├── vm-rollback.sh            # Rollback VM deployment (NEW)
    ├── deploy-cloudrun.sh        # Deploy to Cloud Run
    ├── deploy.sh                 # General deployment script
    ├── pre-deploy.sh             # Pre-deployment checks
    ├── post-deploy.sh            # Post-deployment tasks
    ├── test-local.sh             # Test locally with Docker
    └── verify-deployment.sh      # Verify deployment health
```

---

## ⚙️ Prerequisites

1. **Google Cloud SDK**: Install and configure
   ```bash
   # Install
   curl https://sdk.cloud.google.com | bash
   
   # Authenticate
   gcloud auth login
   ```

2. **Docker** (for Cloud Run): For local testing and Cloud Run deployment
   - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)

3. **Python 3.9+**: For local development
   ```bash
   python --version  # Should be 3.9 or higher
   ```

---

## 🎯 Quick Start - VM Deployment

### First Time Deployment

```bash
# 1. Set up the VM (run once)
./scripts/vm-setup.sh YOUR_PROJECT_ID YOUR_ZONE

# 2. Configure environment variables
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE
sudo nano /opt/avisk/config/.env
# Update DB_PASSWORD, DB_HOST, etc.
# Save and exit (Ctrl+X, Y, Enter)

# 3. Deploy the application
./scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE

# 4. Verify deployment
./scripts/vm-verify.sh YOUR_PROJECT_ID YOUR_ZONE
```

### Update Application

```bash
# Deploy new version
./scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE

# View logs
./scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -f
```

### Access Application

```bash
# Get VM external IP
gcloud compute instances describe avisk-core-services-vm1 \
  --zone=YOUR_ZONE \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Access via browser
# http://<EXTERNAL_IP>:8501
```

---

## 🔧 Environment Variables

### VM Deployment
Stored in `/opt/avisk/config/.env` on the VM:
```env
DEPLOYMENT_ENV=production
DB_PASSWORD=your_password
DB_HOST=your_db_host
DB_NAME=your_db_name
DB_USER=your_db_user
USE_GCS=true
GCS_BUCKET_NAME=avisk-app-data-eb7773c8
```

### Cloud Run Deployment
Set in `cloudbuild-cloudrun.yaml` or via `gcloud` commands:
- `DEPLOYMENT_ENV`: Deployment environment
- `USE_GCS`: Enable GCS for file storage
- `GCS_BUCKET_*`: Google Cloud Storage bucket names

---

## 🧪 Local Testing

Test the application locally before deploying:

```bash
# Using Docker (for Cloud Run deployment)
./scripts/test-local.sh

# Or using Python directly (for VM deployment)
streamlit run main.py
```

---

## 📊 Available Scripts

### VM Management (NEW)
- **vm-setup.sh** - Initial VM setup with all dependencies
- **vm-deploy.sh** - Deploy application code to VM
- **vm-verify.sh** - Verify deployment health
- **vm-logs.sh** - View application logs (supports -f for follow)
- **vm-rollback.sh** - Rollback to previous version

### Cloud Run Management
- **deploy-cloudrun.sh** - Deploy to Cloud Run
- **test-local.sh** - Test Docker container locally
- **verify-deployment.sh** - Verify Cloud Run deployment

### General
- **pre-deploy.sh** - Pre-deployment checks
- **post-deploy.sh** - Post-deployment tasks

---

## 📈 Monitoring and Logging

### VM Deployment
```bash
# View real-time logs
./scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -f

# Last 100 lines
./scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -n 100

# Logs from last hour
./scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -s "1 hour ago"

# Check service status
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE \
  -- sudo systemctl status avisk-core-services
```

### Cloud Run
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Monitor service
gcloud run services describe avisk-core-services --region=us-central1
```

---

## 🔍 Troubleshooting

### VM Deployment

**Service Won't Start**
```bash
# Check logs
./scripts/vm-logs.sh PROJECT_ID ZONE -n 100

# SSH and investigate
gcloud compute ssh avisk-core-services-vm1 --zone=ZONE
sudo systemctl status avisk-core-services
```

**Can't Access Application**
```bash
# Check firewall
gcloud compute firewall-rules list --filter="name~'streamlit'"

# Test from VM
gcloud compute ssh avisk-core-services-vm1 --zone=ZONE -- curl localhost:8501
```

**Rollback to Previous Version**
```bash
# List backups
./scripts/vm-rollback.sh PROJECT_ID ZONE

# Rollback to specific backup
./scripts/vm-rollback.sh PROJECT_ID ZONE avisk-core-services-vm1 app-backup-TIMESTAMP.tar.gz
```

### Cloud Run

1. **Authentication Errors**: `gcloud auth login`
2. **Build Failures**: Check Dockerfile and requirements.txt
3. **Service Won't Start**: Verify port 8080 and environment variables

---

## 🔒 Security Best Practices

1. **Never commit credentials**
   - Use Secret Manager for sensitive data
   - Keep `.env` files in `.gitignore`
   - Manually configure environment on VM

2. **Use IAM properly**
   - Follow principle of least privilege
   - Use service accounts for GCS access

3. **Restrict firewall rules**
   - Limit access to specific IP ranges
   - Use SSH tunnels for development

4. **Regular updates**
   - Keep dependencies updated
   - Monitor security advisories
   - Update VM OS packages regularly

---

## 💰 Cost Optimization

### VM Deployment
- Use appropriate machine type (e2-medium recommended)
- Stop VM when not in use (dev/staging)
- Use committed use discounts for production
- Monitor disk usage

### Cloud Run
- Set minimum instances to 0 for dev/staging
- Use appropriate CPU and memory limits
- Enable request-based scaling

---

## 📚 Documentation

- **[VM_QUICKSTART.md](VM_QUICKSTART.md)** - VM quick reference (⭐ START HERE)
- **[VM_DEPLOYMENT.md](VM_DEPLOYMENT.md)** - Detailed VM deployment guide
- **[DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md)** - Compare deployment options
- **[CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md)** - Cloud Run guide
- [Google Cloud VM Documentation](https://cloud.google.com/compute/docs)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

## 🆘 Getting Help

For issues or questions:
1. Check the deployment logs using appropriate scripts
2. Review the relevant documentation for your deployment type
3. Verify all configuration files
4. Check Google Cloud status page

---

## 🎉 What's New - VM Deployment

- ✅ **vm-setup.sh** - Automated VM setup and configuration
- ✅ **vm-deploy.sh** - Streamlined deployment to VM
- ✅ **vm-verify.sh** - Comprehensive health checks
- ✅ **vm-logs.sh** - Easy log access with multiple options
- ✅ **vm-rollback.sh** - Safe rollback to previous versions
- ✅ **systemd service** - Auto-start on boot
- ✅ **Automatic backups** - Each deployment creates a backup
- ✅ **Log rotation** - Automatic log management
- ✅ **Comprehensive docs** - VM_QUICKSTART.md and VM_DEPLOYMENT.md
