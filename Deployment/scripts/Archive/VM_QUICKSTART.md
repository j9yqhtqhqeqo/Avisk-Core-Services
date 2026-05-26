# Quick Start Guide - VM Deployment

## Deploy to Google Cloud VM: avisk-core-services-vm1

This is a quick reference guide for deploying Avisk Core Services to your Google Cloud VM.

### Prerequisites

- Google Cloud SDK installed and authenticated
- Access to project and VM (avisk-core-services-vm1)
- Project ID and Zone information

### Step-by-Step Deployment

#### 1️⃣ First Time Setup (Run Once)

Set up the VM with all required dependencies:

```bash
cd /Users/mohanganadal/Avisk/Avisk-Core-Services

# Replace with your actual project ID and zone
./Deployment/scripts/vm-setup.sh YOUR_PROJECT_ID YOUR_ZONE
```

Example:
```bash
./Deployment/scripts/vm-setup.sh avisk-production us-central1-a
```

**What this does:**
- Installs Python 3.9 and dependencies
- Creates application directory structure
- Sets up systemd service
- Configures firewall rules
- Creates log rotation

**Time:** ~5-10 minutes

---

#### 2️⃣ Configure Environment (Run Once)

After setup, configure your environment variables:

```bash
# SSH to the VM
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE

# Edit environment configuration
sudo nano /opt/avisk/config/.env

# Update these values:
# - DB_PASSWORD
# - DB_HOST
# - DB_NAME
# - DB_USER
# - GCS credentials if needed

# Save and exit (Ctrl+X, then Y, then Enter)
```

---

#### 3️⃣ Deploy Application Code

Deploy your application to the VM:

```bash
cd /Users/mohanganadal/Avisk/Avisk-Core-Services

./Deployment/scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE
```

Example:
```bash
./Deployment/scripts/vm-deploy.sh avisk-production us-central1-a
```

**What this does:**
- Creates deployment package
- Uploads to VM
- Installs dependencies
- Restarts service
- Verifies deployment

**Time:** ~2-5 minutes

---

#### 4️⃣ Verify Deployment

Verify everything is working:

```bash
./Deployment/scripts/vm-verify.sh YOUR_PROJECT_ID YOUR_ZONE
```

This checks:
- VM status
- Service status
- Application process
- Port availability
- Recent logs
- Disk usage

---

### Common Tasks

#### View Logs

```bash
# Real-time logs (follow mode)
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -f

# Last 100 lines
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -n 100

# Logs from last hour
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -s "1 hour ago"
```

#### Restart Service

```bash
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE \
  -- sudo systemctl restart avisk-core-services
```

#### Check Service Status

```bash
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE \
  -- sudo systemctl status avisk-core-services
```

#### Rollback to Previous Version

```bash
# List available backups
./Deployment/scripts/vm-rollback.sh YOUR_PROJECT_ID YOUR_ZONE

# Rollback to specific backup
./Deployment/scripts/vm-rollback.sh YOUR_PROJECT_ID YOUR_ZONE avisk-core-services-vm1 app-backup-20260129120000.tar.gz
```

---

### Access Your Application

After successful deployment, access your application at:

```
http://<VM_EXTERNAL_IP>:8501
```

Get the external IP:
```bash
gcloud compute instances describe avisk-core-services-vm1 \
  --zone=YOUR_ZONE \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

---

### Troubleshooting

#### Application Won't Start

```bash
# Check logs
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -n 50

# SSH and check manually
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE

# Check service status
sudo systemctl status avisk-core-services

# Check if port is in use
sudo lsof -i :8501
```

#### Can't Access Application

```bash
# Verify firewall rules
gcloud compute firewall-rules list --filter="name~'streamlit'"

# Test from VM itself
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE \
  -- curl localhost:8501
```

#### Service Crashes

```bash
# View error logs
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -n 200

# Check disk space
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE \
  -- df -h

# Check memory
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE \
  -- free -m
```

---

### Update Workflow

When you make code changes:

```bash
# 1. Test locally first
streamlit run main.py

# 2. Commit your changes
git add .
git commit -m "Your changes"
git push

# 3. Deploy to VM
./Deployment/scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE

# 4. Verify
./Deployment/scripts/vm-verify.sh YOUR_PROJECT_ID YOUR_ZONE

# 5. Check logs if needed
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -f
```

---

### Important Files on VM

```
/opt/avisk/
├── app/                          # Application code
├── config/
│   ├── .env                      # Environment variables
│   └── .streamlit/
│       └── config.toml          # Streamlit configuration
├── venv/                         # Python virtual environment
├── logs/                         # Application logs
├── backups/                      # Deployment backups
└── deployment-metadata.json      # Current deployment info
```

---

### Security Checklist

- [ ] Update DB_PASSWORD in `/opt/avisk/config/.env`
- [ ] Configure GCS service account credentials
- [ ] Restrict firewall rules to specific IP ranges
- [ ] Set up SSH key-based authentication
- [ ] Enable automatic security updates on VM
- [ ] Review and restrict IAM permissions

---

### Need Help?

- **Full Documentation**: [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md)
- **View Logs**: `./Deployment/scripts/vm-logs.sh PROJECT_ID ZONE -f`
- **SSH to VM**: `gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE`
- **Service Status**: `sudo systemctl status avisk-core-services`

---

### Useful Commands Reference

```bash
# Get VM info
gcloud compute instances describe avisk-core-services-vm1 --zone=YOUR_ZONE

# SSH to VM
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE

# Copy file to VM
gcloud compute scp local-file.txt avisk-core-services-vm1:/tmp/ --zone=YOUR_ZONE

# Copy file from VM
gcloud compute scp avisk-core-services-vm1:/tmp/remote-file.txt . --zone=YOUR_ZONE

# Stop VM
gcloud compute instances stop avisk-core-services-vm1 --zone=YOUR_ZONE

# Start VM
gcloud compute instances start avisk-core-services-vm1 --zone=YOUR_ZONE

# Restart VM
gcloud compute instances reset avisk-core-services-vm1 --zone=YOUR_ZONE
```
