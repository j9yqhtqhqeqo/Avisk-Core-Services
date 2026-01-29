# 🚀 Getting Started with VM Deployment

Welcome! This guide will help you deploy Avisk Core Services to your Google Cloud VM `avisk-core-services-vm1`.

## ⚡ Quick Start (5 minutes)

### Step 1: Update Configuration

Edit the menu script with your project details:

```bash
nano Deployment/scripts/vm-menu.sh
```

Update these lines:
```bash
PROJECT_ID="your-actual-project-id"
ZONE="us-central1-a"  # or your VM's zone
```

### Step 2: Run the Menu

```bash
./Deployment/scripts/vm-menu.sh
```

Follow the prompts:
1. Choose option **1** for first-time setup
2. SSH to VM and configure environment variables
3. Choose option **2** to deploy the application
4. Choose option **3** to verify everything is working

### Step 3: Access Your Application

Get your VM's IP address (option 9 in menu) and visit:
```
http://<VM_EXTERNAL_IP>:8501
```

## 📖 Documentation Guide

### For Quick Reference
Start here: **[VM_QUICKSTART.md](VM_QUICKSTART.md)**
- Common commands
- Quick troubleshooting
- Essential workflows

### For Detailed Information
Read: **[VM_DEPLOYMENT.md](VM_DEPLOYMENT.md)**
- Complete setup guide
- Architecture details
- Advanced configuration
- Security best practices

### For Comparison
See: **[DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md)**
- VM vs Cloud Run
- Cost analysis
- When to use each

### For Complete Overview
Review: **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)**
- All features
- File structure
- Technical details

## 🔧 Available Scripts

All scripts are in `Deployment/scripts/`:

### Essential Scripts
- **vm-menu.sh** - Interactive menu (easiest way!)
- **vm-setup.sh** - One-time VM setup
- **vm-deploy.sh** - Deploy your application
- **vm-verify.sh** - Check deployment health

### Management Scripts
- **vm-logs.sh** - View application logs
- **vm-rollback.sh** - Rollback to previous version

## 💡 Common Workflows

### First Deployment
```bash
# 1. Setup VM
./Deployment/scripts/vm-setup.sh YOUR_PROJECT_ID YOUR_ZONE

# 2. Configure environment
gcloud compute ssh avisk-core-services-vm1 --zone=YOUR_ZONE
sudo nano /opt/avisk/config/.env
# Update DB_PASSWORD and other variables
# Exit: Ctrl+X, Y, Enter

# 3. Deploy
./Deployment/scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE

# 4. Verify
./Deployment/scripts/vm-verify.sh YOUR_PROJECT_ID YOUR_ZONE
```

### Update Application
```bash
# Make your code changes, then:
./Deployment/scripts/vm-deploy.sh YOUR_PROJECT_ID YOUR_ZONE
```

### View Logs
```bash
# Real-time logs
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -f

# Last 100 lines
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -n 100
```

### Troubleshooting
```bash
# Check status
./Deployment/scripts/vm-verify.sh YOUR_PROJECT_ID YOUR_ZONE

# View logs
./Deployment/scripts/vm-logs.sh YOUR_PROJECT_ID YOUR_ZONE -n 200

# Rollback if needed
./Deployment/scripts/vm-rollback.sh YOUR_PROJECT_ID YOUR_ZONE
```

## 🎯 What You Need

### Before You Start
1. ✅ Google Cloud SDK installed
2. ✅ Authenticated with `gcloud auth login`
3. ✅ VM `avisk-core-services-vm1` created
4. ✅ Your project ID and zone information

### For First Deployment
1. Database credentials (DB_PASSWORD, DB_HOST, etc.)
2. GCS bucket name (if using GCS)
3. Any other environment-specific settings

## 🔒 Security Checklist

Before going to production:

- [ ] Update DB_PASSWORD in `/opt/avisk/config/.env`
- [ ] Restrict firewall to specific IP ranges
- [ ] Set up SSH key authentication
- [ ] Configure GCS service account properly
- [ ] Review and test backup/restore process
- [ ] Set up monitoring and alerting

## 🆘 Need Help?

### Quick Help
- **Interactive Menu**: `./Deployment/scripts/vm-menu.sh`
- **Quick Reference**: [VM_QUICKSTART.md](VM_QUICKSTART.md)
- **View Logs**: `./Deployment/scripts/vm-logs.sh PROJECT_ID ZONE -f`

### Documentation
- [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md) - Complete guide
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - Technical details
- [README.md](README.md) - All deployment options

### Troubleshooting
1. Check service: `./Deployment/scripts/vm-verify.sh PROJECT_ID ZONE`
2. View logs: `./Deployment/scripts/vm-logs.sh PROJECT_ID ZONE -n 100`
3. SSH to VM: `gcloud compute ssh avisk-core-services-vm1 --zone=ZONE`
4. Check status: `sudo systemctl status avisk-core-services`

## 🎉 What's Included

- ✅ Automated VM setup and configuration
- ✅ systemd service with auto-start
- ✅ Automatic backups before each deployment
- ✅ Easy log viewing and monitoring
- ✅ Safe rollback capabilities
- ✅ Health checking and verification
- ✅ Interactive menu for common tasks
- ✅ Comprehensive documentation

## 📋 Next Steps

1. **Deploy Now**: Use `./Deployment/scripts/vm-menu.sh`
2. **Learn More**: Read [VM_QUICKSTART.md](VM_QUICKSTART.md)
3. **Optimize**: Review [DEPLOYMENT_COMPARISON.md](DEPLOYMENT_COMPARISON.md)
4. **Secure**: Follow security checklist above

---

**Ready to deploy?** Run:
```bash
./Deployment/scripts/vm-menu.sh
```

Or jump straight to setup:
```bash
./Deployment/scripts/vm-setup.sh YOUR_PROJECT_ID YOUR_ZONE
```

Good luck! 🚀
