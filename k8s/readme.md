# DiSh Job - Kubernetes Deployment

Simple single-file Kubernetes deployment for the DiSh (Docker-based Shopify Ingestion) job.

## 🚀 Quick Start

### 1. Build and prepare the Docker image

```bash
# Build the image
docker build -t dish-job:latest ./job/

# If using a registry, tag and push
# docker tag dish-job:latest your-registry.com/dish-job:latest
# docker push your-registry.com/dish-job:latest
```

### 2. Configure the manifest

Edit `dish-k8s.yaml` and update these values:

```yaml
# In the Secret section:
stringData:
  shopify-pat: "your-actual-shopify-pat-token"
  bloomreach-token: "your-actual-bloomreach-api-token"

# In the ConfigMap section:
data:
  shopify-url: "your-store.myshopify.com"
  br-account-id: "1234"  # Your 4-digit account ID
  br-catalog-name: "your-catalog-name"
  br-environment: "production"  # or "staging"
```

### 3. Deploy to Kubernetes

```bash
kubectl apply -f dish-k8s.yaml
```

## 📋 What Gets Created

- **Namespace**: `dish-system` - isolated environment
- **Secret**: Stores Shopify PAT and Bloomreach API tokens
- **ConfigMap**: Stores non-sensitive configuration
- **PVC**: 5GB storage for export files
- **Job**: `dish-full-feed` - for manual full catalog syncs
- **CronJob**: `dish-delta-feed` - automatic delta updates every 15 minutes

## 🏃 Running Jobs

### Manual Full Feed

```bash
# Create a new job from the template
kubectl create job dish-full-$(date +%s) --from=job/dish-full-feed -n dish-system

# Watch the job
kubectl get jobs -n dish-system -w

# View logs
kubectl logs -f job/dish-full-$(kubectl get jobs -n dish-system --sort-by=.metadata.creationTimestamp -o name | tail -1 | cut -d/ -f2) -n dish-system
```

### Check Delta Feed Status

```bash
# View CronJob status
kubectl get cronjobs -n dish-system

# View recent delta jobs
kubectl get jobs -n dish-system -l type=delta-feed

# View logs from latest delta job
kubectl logs -n dish-system $(kubectl get pods -n dish-system -l type=delta-feed --sort-by=.metadata.creationTimestamp -o name | tail -1)
```

## ⚙️ Configuration Options

### Environment Settings

Update the ConfigMap in the manifest:

```yaml
data:
  # Required
  shopify-url: "your-store.myshopify.com"
  br-environment: "production"  # or "staging"
  br-account-id: "1234"
  br-catalog-name: "your-catalog"
  
  # Optional
  log-level: "INFO"           # DEBUG, INFO, WARNING, ERROR
  auto-index: "true"          # Auto-trigger indexing after feed
  multi-market: "false"       # Enable multi-market support
  market-cache-enabled: "true" # Cache market data for delta feeds
```

### Multi-Market Setup

For multi-market stores, update the ConfigMap:

```yaml
data:
  multi-market: "true"
  shopify-market: "US"        # Add this
  shopify-language: "en"      # Add this
```

Then add these environment variables to both Job and CronJob containers:

```yaml
env:
- name: SHOPIFY_MARKET
  valueFrom:
    configMapKeyRef:
      name: dish-config
      key: shopify-market
- name: SHOPIFY_LANGUAGE
  valueFrom:
    configMapKeyRef:
      name: dish-config
      key: shopify-language
```

### Change Delta Schedule

Edit the CronJob schedule:

```yaml
spec:
  schedule: "*/30 * * * *"  # Every 30 minutes
  # schedule: "0 * * * *"   # Every hour
  # schedule: "0 */6 * * *" # Every 6 hours
```

## 📊 Monitoring

### Check Status

```bash
# Overview
kubectl get all -n dish-system

# Job history
kubectl get jobs -n dish-system --sort-by=.metadata.creationTimestamp

# Storage usage
kubectl get pvc -n dish-system

# Events
kubectl get events -n dish-system --sort-by=.lastTimestamp
```

### View Logs

```bash
# Current running job
kubectl logs -f -n dish-system -l app=dish-job

# Specific job
kubectl logs -n dish-system job/dish-full-feed-1234567890

# All recent logs
kubectl logs -n dish-system --since=1h -l app=dish-job
```

### Resource Usage

```bash
# Pod resource usage (requires metrics-server)
kubectl top pods -n dish-system

# Storage usage
kubectl describe pvc dish-storage -n dish-system
```

## 🔧 Troubleshooting

### Common Issues

**Job fails with ImagePullBackOff**:
```bash
# Check if image exists
kubectl describe pod -n dish-system <pod-name>

# Update image if needed
kubectl set image job/dish-full-feed dish-job=dish-job:v1.1 -n dish-system
```

**Out of memory errors**:
```bash
# Increase memory limits in the manifest
resources:
  limits:
    memory: "8Gi"  # Increase from 4Gi
```

**CronJob not running**:
```bash
# Check CronJob status
kubectl describe cronjob dish-delta-feed -n dish-system

# Check for scheduling issues
kubectl get events -n dish-system | grep -i cron
```

**Storage issues**:
```bash
# Check PVC status
kubectl describe pvc dish-storage -n dish-system

# Check available storage classes
kubectl get storageclass
```

### Debug Commands

```bash
# Get into a running container
kubectl exec -it <pod-name> -n dish-system -- /bin/bash

# Check job details
kubectl describe job <job-name> -n dish-system

# Force delete stuck jobs
kubectl delete job <job-name> -n dish-system --force --grace-period=0
```

## 🧹 Cleanup

### Remove old jobs

```bash
# Delete completed jobs older than 1 day
kubectl get jobs -n dish-system -o json | \
  jq -r '.items[] | select(.status.completionTime != null) | select(.status.completionTime < "'$(date -d '1 day ago' -u +%Y-%m-%dT%H:%M:%SZ)'") | .metadata.name' | \
  xargs -I {} kubectl delete job {} -n dish-system

# Delete failed jobs
kubectl delete jobs -n dish-system --field-selector status.successful=0
```

### Update secrets

```bash
# Update tokens
kubectl patch secret dish-secrets -n dish-system -p='{"stringData":{"shopify-pat":"new-token"}}'
kubectl patch secret dish-secrets -n dish-system -p='{"stringData":{"bloomreach-token":"new-token"}}'

# Restart jobs to pick up new secrets
kubectl delete jobs -n dish-system -l app=dish-job
```

### Complete removal

```bash
# Delete everything
kubectl delete namespace dish-system
```

## 📈 Scaling

### For larger catalogs

Increase resources in the manifest:

```yaml
# Full feed job resources
resources:
  requests:
    memory: "4Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "2000m"

# Increase storage
resources:
  requests:
    storage: 20Gi
```

### For more frequent updates

```yaml
# Run delta every 5 minutes
schedule: "*/5 * * * *"

# Or every minute (not recommended)
schedule: "* * * * *"
```

## 🔒 Security Notes

- Store sensitive tokens in Kubernetes Secrets, not ConfigMaps
- Use least-privilege access if implementing RBAC
- Consider using external secret management (HashiCorp Vault, etc.)
- Regularly rotate API tokens

## 📝 License

Proprietary - Bloomreach, Inc.