# Deployment Scripts Comparison: Cloud Run vs VM

This document compares the deployment approaches for Avisk Core Services on Google Cloud Run vs Google Cloud VM.

## Overview

| Aspect | Cloud Run | VM Deployment |
|--------|-----------|---------------|
| **Deployment Model** | Container-based, fully managed | Direct deployment on VM |
| **Scaling** | Automatic (0 to N instances) | Manual/Fixed |
| **Cost Model** | Pay-per-request | Fixed VM cost |
| **Management** | Fully managed by Google | Self-managed |
| **Startup Time** | Cold starts possible | Always running |
| **Port** | 8080 | 8501 |
| **Configuration** | Environment variables in Cloud Run service | `.env` file on VM |

## When to Use Each

### Use Cloud Run When:
- ✅ You want automatic scaling
- ✅ You have variable traffic patterns
- ✅ You want to pay only for actual usage
- ✅ You prefer minimal operational overhead
- ✅ You can tolerate cold starts

### Use VM Deployment When:
- ✅ You need predictable performance (no cold starts)
- ✅ You have consistent traffic
- ✅ You need full control over the environment
- ✅ You want to run additional services on the same instance
- ✅ You have specific OS or system-level requirements

## Deployment Scripts

### Cloud Run Scripts

Located in `Deployment/scripts/`:

1. **deploy-cloudrun.sh** - Deploy to Cloud Run
   ```bash
   ./Deployment/scripts/deploy-cloudrun.sh PROJECT_ID REGION
   ```

2. **test-local.sh** - Test Docker container locally
   ```bash
   ./Deployment/scripts/test-local.sh
   ```

3. **verify-deployment.sh** - Verify Cloud Run deployment
   ```bash
   ./Deployment/scripts/verify-deployment.sh PROJECT_ID REGION
   ```

### VM Scripts

Located in `Deployment/scripts/`:

1. **vm-setup.sh** - One-time VM setup
   ```bash
   ./Deployment/scripts/vm-setup.sh PROJECT_ID ZONE
   ```

2. **vm-deploy.sh** - Deploy application code to VM
   ```bash
   ./Deployment/scripts/vm-deploy.sh PROJECT_ID ZONE
   ```

3. **vm-verify.sh** - Verify VM deployment
   ```bash
   ./Deployment/scripts/vm-verify.sh PROJECT_ID ZONE
   ```

4. **vm-logs.sh** - View application logs
   ```bash
   ./Deployment/scripts/vm-logs.sh PROJECT_ID ZONE -f
   ```

5. **vm-rollback.sh** - Rollback to previous version
   ```bash
   ./Deployment/scripts/vm-rollback.sh PROJECT_ID ZONE
   ```

## Architecture Differences

### Cloud Run Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Load Balancer      │
│  (Cloud Run)        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Container Instance │
│  (Auto-scaled)      │
│  Port: 8080         │
└─────────────────────┘
```

### VM Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  VM External IP     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  systemd Service    │
│  Streamlit App      │
│  Port: 8501         │
└─────────────────────┘
```

## Configuration Management

### Cloud Run

Environment variables set via:
- `cloudbuild-cloudrun.yaml`
- `gcloud run services update` command

Example:
```yaml
env:
  - name: DEPLOYMENT_ENV
    value: production
  - name: USE_GCS
    value: "true"
```

### VM

Environment variables in `/opt/avisk/config/.env`:
```env
DEPLOYMENT_ENV=production
USE_GCS=true
DB_PASSWORD=secret
```

## Cost Comparison

### Cloud Run (Example)
- **CPU**: 1 vCPU @ $0.00002400/vCPU-second
- **Memory**: 1 GiB @ $0.00000250/GiB-second
- **Requests**: $0.40/million requests
- **Free Tier**: 2 million requests/month

**Typical Monthly Cost**: $5-50 (varies with traffic)

### VM (Example: e2-medium)
- **Machine Type**: e2-medium (2 vCPU, 4 GB)
- **Monthly Cost**: ~$24.27 (24/7 operation)
- **Disk**: +$0.040/GB/month

**Typical Monthly Cost**: $25-40 (fixed)

## Deployment Process Comparison

### Cloud Run Deployment

```bash
# 1. Build and deploy (single command)
gcloud builds submit --config=Deployment/cloudbuild-cloudrun.yaml .

# 2. Verify
./Deployment/scripts/verify-deployment.sh PROJECT_ID REGION
```

**Time**: ~5-10 minutes

### VM Deployment

```bash
# 1. One-time setup
./Deployment/scripts/vm-setup.sh PROJECT_ID ZONE

# 2. Configure environment
gcloud compute ssh avisk-core-services-vm1 --zone=ZONE
sudo nano /opt/avisk/config/.env

# 3. Deploy code
./Deployment/scripts/vm-deploy.sh PROJECT_ID ZONE

# 4. Verify
./Deployment/scripts/vm-verify.sh PROJECT_ID ZONE
```

**Time**: 
- Initial setup: ~10-15 minutes
- Subsequent deployments: ~2-5 minutes

## Monitoring and Logging

### Cloud Run

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=avisk-core-services" --limit 50

# Metrics in Cloud Console
# Automatically integrated with Cloud Monitoring
```

### VM

```bash
# View logs
./Deployment/scripts/vm-logs.sh PROJECT_ID ZONE -f

# Or SSH and use journalctl
gcloud compute ssh avisk-core-services-vm1 --zone=ZONE
sudo journalctl -u avisk-core-services -f
```

## Maintenance

### Cloud Run

- ✅ Automatic OS and runtime updates
- ✅ Automatic SSL certificate management
- ✅ Built-in load balancing
- ❌ Less control over environment

### VM

- ❌ Manual OS updates required
- ❌ Manual SSL setup (if needed)
- ❌ Manual load balancing setup
- ✅ Full control over environment

## Migration Path

### From Cloud Run to VM

1. Run VM setup: `vm-setup.sh`
2. Configure environment variables
3. Deploy code: `vm-deploy.sh`
4. Update DNS to point to VM IP
5. Monitor and verify

### From VM to Cloud Run

1. Ensure application works in containers
2. Update port from 8501 to 8080
3. Update environment variable handling
4. Deploy to Cloud Run
5. Update DNS to Cloud Run URL

## Recommendations

### Development/Testing
**Recommended**: VM Deployment
- Easier debugging
- Direct access to file system
- No cold starts

### Production (Low-Medium Traffic)
**Recommended**: Cloud Run
- Lower operational overhead
- Cost-effective for variable traffic
- Automatic scaling

### Production (High/Consistent Traffic)
**Recommended**: VM Deployment or Kubernetes
- No cold starts
- Predictable costs
- Better performance consistency

## Summary

Both deployment methods are valid, and the choice depends on your specific requirements:

- **Choose Cloud Run** for simplicity, automatic scaling, and variable traffic
- **Choose VM** for full control, predictable performance, and consistent traffic

The scripts provided in this repository support both deployment methods, allowing you to switch between them based on your needs.
