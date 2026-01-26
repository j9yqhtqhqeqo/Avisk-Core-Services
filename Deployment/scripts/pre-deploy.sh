#!/bin/bash
set -e

# Pre-deployment checks for Avisk Core Services

ENVIRONMENT=${1:-"development"}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "🔍 Running pre-deployment checks for $ENVIRONMENT environment"

# Check Google Cloud authentication
echo "Checking Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ No active Google Cloud authentication found"
    echo "Run: gcloud auth login"
    exit 1
fi
echo "✅ Google Cloud authentication verified"

# Check required environment variables
echo "Checking environment variables..."
required_vars=("DEPLOYMENT_ENV")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done
echo "✅ Environment variables verified"

# Validate PathConfiguration
echo "Validating PathConfiguration..."
cd "$PROJECT_ROOT"
if ! python -c "
import os
os.environ['DEPLOYMENT_ENV'] = '$ENVIRONMENT'
from Utilities.PathConfiguration import PathConfiguration
config = PathConfiguration()
print(f'Environment: {config.get_environment_name()}')
print(f'GCS Bucket: {config.get_gcs_bucket_name()}')
print(f'GCS Prefix: {config.get_gcs_prefix()}')
print('✅ PathConfiguration is valid')
"; then
    echo "❌ PathConfiguration validation failed"
    exit 1
fi

# Check GCS bucket access
echo "Checking GCS bucket access..."
if ! python -c "
import os
os.environ['DEPLOYMENT_ENV'] = '$ENVIRONMENT'
from Utilities.PathConfiguration import PathConfiguration
try:
    from google.cloud import storage
    config = PathConfiguration()
    client = storage.Client()
    bucket = client.bucket(config.get_gcs_bucket_name())
    if bucket.exists():
        print(f'✅ GCS bucket {config.get_gcs_bucket_name()} is accessible')
    else:
        print(f'❌ GCS bucket {config.get_gcs_bucket_name()} does not exist')
        exit(1)
except Exception as e:
    print(f'❌ GCS access error: {e}')
    exit(1)
"; then
    echo "❌ GCS bucket access check failed"
    exit 1
fi

# Check for required files
echo "Checking required deployment files..."
required_files=(
    "Deployment/app.yaml"
    "Utilities/PathConfiguration.py"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
        echo "❌ Required file not found: $file"
        exit 1
    fi
done
echo "✅ Required files verified"

# Syntax check for Python files
echo "Running Python syntax checks..."
if ! find "$PROJECT_ROOT" -name "*.py" -not -path "*/Storage Setup/*" -exec python -m py_compile {} \; 2>/dev/null; then
    echo "❌ Python syntax errors found"
    exit 1
fi
echo "✅ Python syntax checks passed"

echo "✅ All pre-deployment checks passed for $ENVIRONMENT!"