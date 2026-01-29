# Deployment Configuration

This directory contains all files and configurations for deploying Avisk Core Services to cloud platforms.

## Structure

```
Deployment/
├── README.md                    # This file
├── app.yaml                     # App Engine deployment config
├── cloudbuild.yaml             # Cloud Build configuration
├── requirements.txt            # Production dependencies
├── deployment-config.yaml     # Environment-specific configurations
├── scripts/
│   ├── deploy.sh              # Main deployment script
│   ├── pre-deploy.sh          # Pre-deployment checks
│   └── post-deploy.sh         # Post-deployment verification
└── environments/
    ├── development.yaml       # Development environment config
    ├── test.yaml             # Test environment config
    └── production.yaml       # Production environment config
```

## Deployment Process

### Prerequisites
- Google Cloud SDK installed and authenticated
- Access to the `avisk-app-data-eb7773c8` bucket
- Proper IAM permissions for the target project

### Quick Deploy
```bash
# Deploy to development (default)
./scripts/deploy-cloudrun.sh [PROJECT_ID] [REGION]

# Deploy to specific environment
./scripts/deploy-cloudrun.sh [PROJECT_ID] [REGION] development
./scripts/deploy-cloudrun.sh [PROJECT_ID] [REGION] test
./scripts/deploy-cloudrun.sh [PROJECT_ID] [REGION] production

# Examples:
./scripts/deploy-cloudrun.sh my-dev-project us-central1 development
./scripts/deploy-cloudrun.sh my-prod-project us-central1 production
```

### Manual Deploy Steps
1. Set environment variables for target environment
2. Run pre-deployment checks
3. Build and deploy application
4. Run post-deployment verification

## Environment Configuration

Each environment uses the existing GCS bucket with appropriate prefixes:
- **Development**: `Development/` folder in `avisk-app-data-eb7773c8`
- **Test**: `Test/` folder in `avisk-app-data-eb7773c8`
- **Production**: `Production/` folder in `avisk-app-data-eb7773c8`

## Environment Variables

Required environment variables for deployment:
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account key
- `DEPLOYMENT_ENV` - Target environment (development/test/production)
- `GCS_BUCKET_*` - Override default bucket names if needed

## Security

- Service account credentials are managed separately
- Environment-specific secrets are configured in Google Cloud Secret Manager
- No sensitive data is stored in deployment files

## Monitoring

Post-deployment verification includes:
- Application health checks
- GCS connectivity tests
- Log file access verification
- Database connection validation