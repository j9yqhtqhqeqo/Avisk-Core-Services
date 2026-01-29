# VM Deployment Scripts - Summary

## What Was Created

Complete deployment infrastructure for deploying Avisk Core Services to Google Cloud VM `avisk-core-services-vm1`.

## Files Created

### Documentation (5 files)
1. **VM_QUICKSTART.md** - Quick reference guide for common tasks
2. **VM_DEPLOYMENT.md** - Comprehensive deployment documentation
3. **DEPLOYMENT_COMPARISON.md** - Comparison between VM and Cloud Run
4. **README.md** - Updated main deployment README
5. **DEPLOYMENT_SUMMARY.md** - This file

### Scripts (5 executable files)
1. **scripts/vm-setup.sh** - One-time VM initialization
2. **scripts/vm-deploy.sh** - Application deployment
3. **scripts/vm-verify.sh** - Health verification
4. **scripts/vm-logs.sh** - Log viewing
5. **scripts/vm-rollback.sh** - Rollback management

## Key Features

### 1. Automated Setup (vm-setup.sh)
- Installs Python 3.9 and system dependencies
- Creates application user and directory structure
- Sets up systemd service for auto-start
- Configures environment variables
- Creates Streamlit configuration
- Sets up log rotation
- Configures firewall rules

### 2. Streamlined Deployment (vm-deploy.sh)
- Creates deployment package
- Uploads to VM via gcloud scp
- Backs up current deployment
- Installs Python dependencies
- Restarts service
- Verifies deployment success

### 3. Comprehensive Verification (vm-verify.sh)
- Checks VM status
- Verifies service is running
- Tests application process
- Checks port availability
- Reviews recent logs
- Displays deployment metadata

### 4. Easy Log Access (vm-logs.sh)
- Real-time log following (-f flag)
- Configurable line count (-n flag)
- Time-based filtering (-s flag)
- Uses journalctl for systemd integration

### 5. Safe Rollback (vm-rollback.sh)
- Lists available backups
- Interactive rollback confirmation
- Creates pre-rollback backup
- Restores previous version
- Verifies service after rollback

## Architecture

### On VM: /opt/avisk/
```
/opt/avisk/
├── app/                    # Application code
│   ├── main.py
│   ├── Services/
│   ├── DBEntities/
│   └── ...
├── venv/                   # Python virtual environment
├── config/
│   ├── .env               # Environment variables
│   └── .streamlit/
│       └── config.toml    # Streamlit config
├── logs/                   # Application logs
├── backups/               # Deployment backups
└── deployment-metadata.json
```

### systemd Service
- **Service Name**: avisk-core-services
- **User**: avisk
- **Working Directory**: /opt/avisk/app
- **Command**: streamlit run main.py --server.port=8501
- **Auto-start**: Enabled on boot
- **Restart**: Always (with 10s delay)

## Deployment Workflow

### First Time Setup
```bash
1. vm-setup.sh       # Initialize VM (~10 min)
2. Configure .env    # Set environment variables
3. vm-deploy.sh      # Deploy application (~3 min)
4. vm-verify.sh      # Verify deployment
```

### Regular Updates
```bash
1. vm-deploy.sh      # Deploy new version
2. vm-verify.sh      # Verify deployment
3. vm-logs.sh -f     # Monitor if needed
```

### Troubleshooting
```bash
1. vm-verify.sh      # Check current status
2. vm-logs.sh -n 100 # View logs
3. vm-rollback.sh    # Rollback if needed
```

## Environment Configuration

### Required Variables (in /opt/avisk/config/.env)
```env
DEPLOYMENT_ENV=production
DB_PASSWORD=<your_password>
DB_HOST=<your_db_host>
DB_NAME=<your_db_name>
DB_USER=<your_db_user>
USE_GCS=true
GCS_BUCKET_NAME=avisk-app-data-eb7773c8
```

### Streamlit Configuration
- Port: 8501
- Address: 0.0.0.0 (all interfaces)
- Headless: true
- CORS: disabled
- Max upload: 200MB

## Firewall Configuration

### GCP Firewall Rule
- **Rule Name**: allow-streamlit-8501
- **Target**: All instances (or specific tags)
- **Port**: tcp:8501
- **Source**: 0.0.0.0/0 (customize for production)

### VM Firewall (ufw)
- Automatically configured by vm-setup.sh
- Allows port 8501/tcp

## Monitoring

### Service Status
```bash
sudo systemctl status avisk-core-services
sudo systemctl is-active avisk-core-services
sudo systemctl is-enabled avisk-core-services
```

### Logs
```bash
# Real-time
sudo journalctl -u avisk-core-services -f

# Last N lines
sudo journalctl -u avisk-core-services -n 100

# Since time
sudo journalctl -u avisk-core-services --since "1 hour ago"
```

### Process
```bash
ps aux | grep streamlit
pgrep -f "streamlit run main.py"
```

### Network
```bash
sudo netstat -tulpn | grep :8501
sudo lsof -i :8501
```

## Backup Strategy

### Automatic Backups
- Created before each deployment
- Stored in /opt/avisk/backups/
- Named: app-backup-YYYYMMDDHHMMSS.tar.gz
- Last 5 backups retained

### Manual Backup
```bash
sudo tar -czf /opt/avisk/backups/manual-backup-$(date +%Y%m%d).tar.gz \
  /opt/avisk/app /opt/avisk/config
```

## Security Features

1. **Dedicated User**: Application runs as 'avisk' user
2. **No New Privileges**: systemd security setting
3. **Private Tmp**: Isolated temporary directory
4. **Environment Files**: Secure storage of credentials
5. **Firewall Rules**: Configurable access control

## Comparison with Cloud Run

| Aspect | VM Deployment | Cloud Run |
|--------|---------------|-----------|
| Setup Complexity | Medium | Low |
| Ongoing Management | Self-managed | Fully managed |
| Scaling | Manual | Automatic |
| Cost (typical) | $25-40/mo | $5-50/mo |
| Cold Starts | None | Possible |
| Control | Full | Limited |
| Port | 8501 | 8080 |
| SSL | Manual setup | Automatic |

## Next Steps

### Immediate
1. Run vm-setup.sh on your VM
2. Configure environment variables
3. Deploy application with vm-deploy.sh
4. Verify with vm-verify.sh

### Production Readiness
1. Set up SSL/TLS (nginx reverse proxy)
2. Configure proper firewall rules (restrict IPs)
3. Set up monitoring and alerting
4. Configure automated backups to GCS
5. Implement log aggregation
6. Set up uptime monitoring

### Recommended Enhancements
1. **Nginx Reverse Proxy**
   - SSL termination
   - Custom domain
   - Request limiting

2. **Load Balancer**
   - Multiple VM instances
   - Health checks
   - Session persistence

3. **Cloud Monitoring**
   - Custom metrics
   - Alerting policies
   - Log-based metrics

4. **CI/CD Pipeline**
   - Automated deployments
   - Testing before deploy
   - Rollback capabilities

## Useful Commands

### VM Management
```bash
# Start/stop/restart VM
gcloud compute instances start avisk-core-services-vm1 --zone=ZONE
gcloud compute instances stop avisk-core-services-vm1 --zone=ZONE
gcloud compute instances reset avisk-core-services-vm1 --zone=ZONE

# SSH to VM
gcloud compute ssh avisk-core-services-vm1 --zone=ZONE

# Get external IP
gcloud compute instances describe avisk-core-services-vm1 \
  --zone=ZONE \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### Service Management
```bash
# Start/stop/restart service
sudo systemctl start avisk-core-services
sudo systemctl stop avisk-core-services
sudo systemctl restart avisk-core-services

# Enable/disable auto-start
sudo systemctl enable avisk-core-services
sudo systemctl disable avisk-core-services

# View status
sudo systemctl status avisk-core-services
```

### File Transfer
```bash
# Upload to VM
gcloud compute scp local-file.txt avisk-core-services-vm1:/tmp/ --zone=ZONE

# Download from VM
gcloud compute scp avisk-core-services-vm1:/tmp/remote-file.txt . --zone=ZONE

# Upload directory
gcloud compute scp --recurse local-dir/ avisk-core-services-vm1:/tmp/ --zone=ZONE
```

## Troubleshooting Guide

### Service Won't Start
1. Check logs: `sudo journalctl -u avisk-core-services -n 50`
2. Check Python path: `which python3`
3. Verify dependencies: `/opt/avisk/venv/bin/pip list`
4. Check environment: `cat /opt/avisk/config/.env`

### Can't Access Application
1. Check service: `sudo systemctl status avisk-core-services`
2. Check port: `sudo netstat -tulpn | grep :8501`
3. Check firewall: `gcloud compute firewall-rules list`
4. Test locally: `curl localhost:8501`

### High Memory/CPU Usage
1. Check process: `ps aux | grep streamlit`
2. Check system resources: `top` or `htop`
3. Review logs for errors
4. Consider upgrading VM machine type

### Disk Space Issues
1. Check disk usage: `df -h`
2. Clean old backups: `ls -lh /opt/avisk/backups/`
3. Clean Python cache: `find /opt/avisk -name __pycache__ -delete`
4. Check log files: `du -sh /opt/avisk/logs/`

## Support Resources

- **Documentation**: VM_QUICKSTART.md, VM_DEPLOYMENT.md
- **Logs**: `./scripts/vm-logs.sh PROJECT_ID ZONE -f`
- **SSH Access**: `gcloud compute ssh avisk-core-services-vm1 --zone=ZONE`
- **Service Status**: `sudo systemctl status avisk-core-services`
- **Health Check**: `./scripts/vm-verify.sh PROJECT_ID ZONE`

## Conclusion

You now have a complete, production-ready deployment solution for your Google Cloud VM. The scripts handle:

✅ Complete VM setup and configuration  
✅ Automated deployments with backups  
✅ Service management and monitoring  
✅ Easy log access and troubleshooting  
✅ Safe rollback capabilities  

Start with **VM_QUICKSTART.md** for a quick reference guide, or refer to **VM_DEPLOYMENT.md** for comprehensive documentation.
