# Cloud Run Deployment Guide for Avisk Core Services

This guide explains how to deploy the Avisk Core Services application to Google Cloud Run.

## Prerequisites

1. **Google Cloud SDK**: Install and authenticate
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

2. **Docker**: Install Docker Desktop for local testing

3. **Google Cloud Project**: Create a project and enable billing

## Deployment Steps

### Step 1: Local Testing (Recommended)

Test the application locally before deploying:

```bash
# Run local test
./Deployment/scripts/test-local.sh
```

This will:
- Build the Docker image
- Run it locally on port 8080
- Test health endpoints
- Provide access URLs

### Step 2: Deploy to Cloud Run

Deploy using the automated script:

```bash
# Deploy to Cloud Run (replace with your project ID)
./Deployment/scripts/deploy-cloudrun.sh YOUR_PROJECT_ID us-central1
```

Or deploy manually:

```bash
# Set your project
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Deploy using Cloud Build
gcloud builds submit --config=Deployment/cloudbuild-cloudrun.yaml .
```

### Step 3: Configure Environment

The deployment automatically sets these environment variables:
- `DEPLOYMENT_ENV=production`
- `GCS_BUCKET_*=avisk-app-data-eb7773c8`
- `USE_GCS=true`

To update environment variables:

```bash
gcloud run services update avisk-core-services \
    --region=us-central1 \
    --set-env-vars="NEW_VAR=value"
```

## Configuration Options

### Resource Limits

Current configuration (modify in [cloudbuild-cloudrun.yaml](cloudbuild-cloudrun.yaml)):
- **Memory**: 1Gi
- **CPU**: 1 vCPU
- **Max Instances**: 10
- **Min Instances**: 1
- **Request Timeout**: 3600s (1 hour)

### Scaling

Cloud Run automatically scales based on traffic:
- Scales to zero when no traffic
- Scales up to handle increased load
- Concurrent requests per instance: 80

## Security

### Authentication

The service is currently deployed with `--allow-unauthenticated`. To secure it:

```bash
# Remove unauthenticated access
gcloud run services update avisk-core-services \
    --region=us-central1 \
    --no-allow-unauthenticated

# Grant access to specific users
gcloud run services add-iam-policy-binding avisk-core-services \
    --region=us-central1 \
    --member="user:user@example.com" \
    --role="roles/run.invoker"
```

### Secrets Management

For sensitive data, use Google Secret Manager:

```bash
# Create a secret
gcloud secrets create db-password --data-file=password.txt

# Use in Cloud Run
gcloud run services update avisk-core-services \
    --region=us-central1 \
    --set-secrets="DB_PASSWORD=db-password:latest"
```

## Monitoring and Logging

### View Logs

```bash
# Real-time logs
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=avisk-core-services"

# Logs from specific time
gcloud logs read "resource.type=cloud_run_revision" \
    --since="2024-01-01T00:00:00Z" \
    --format="table(timestamp,severity,textPayload)"
```

### Metrics Dashboard

Access metrics at: https://console.cloud.google.com/run/detail/REGION/avisk-core-services/metrics

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs
   gcloud builds log [BUILD_ID]
   ```

2. **Service Not Starting**
   ```bash
   # Check service logs
   gcloud run services logs read avisk-core-services --region=us-central1
   ```

3. **Database Connection Issues**
   - Ensure Cloud SQL proxy is configured correctly
   - Check VPC connector settings
   - Verify database credentials

### Health Checks

- **Health Endpoint**: `https://your-service-url/health`
- **Main App**: `https://your-service-url`

## Cost Optimization

1. **Adjust Resources**: Right-size CPU and memory based on usage
2. **Min Instances**: Set to 0 for cost savings if cold starts are acceptable
3. **Request Timeout**: Reduce if your app doesn't need long-running requests

## Migration from App Engine

Key differences from your previous App Engine setup:

| Aspect | App Engine | Cloud Run |
|--------|------------|-----------|
| Configuration | app.yaml | Dockerfile + cloudbuild.yaml |
| Scaling | Automatic | Container-based scaling |
| Pricing | Instance hours | Request-based |
| Cold Starts | Minimal | Can occur with scale-to-zero |
| File System | Read-only (except tmp) | Read-only container |

## Next Steps

1. **Set up CI/CD**: Connect to GitHub for automatic deployments
2. **Custom Domain**: Map your domain to the Cloud Run service
3. **Load Testing**: Use Cloud Load Testing to validate performance
4. **Monitoring**: Set up alerts for errors and performance metrics

For questions or issues, refer to the [Cloud Run documentation](https://cloud.google.com/run/docs).