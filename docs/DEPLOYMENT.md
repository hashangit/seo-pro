# SEO Pro - SaaS Deployment Guide

This guide covers deploying the SEO Pro SaaS platform to production.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SEO PRO SAAS                                  │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Next.js   │  │  FastAPI     │  │  Supabase    │
    │ Frontend    │◄─┤  Gateway     │◄─┤  PostgreSQL  │
    │ (Vercel)    │  │ (Cloud Run)  │  │ (Data only)  │
    └─────────────┘  └──────┬───────┘  └──────────────┘
                            │
                            │ Cloud Tasks
                            │ (sdk-worker-queue)
                            ▼
                   ┌──────────────────┐
                   │   SDK Worker     │
                   │  (Cloud Run)     │
                   │                  │
                   │ Claude Agent SDK │
                   │ → GLM-4.7 (Z.AI) │
                   │ Playwright CLI   │
                   └──────────────────┘
```

## Prerequisites

### 1. Google Cloud Project

```bash
# Create project
gcloud projects create seo-pro-production

# Set default
gcloud config set project seo-pro-production

# Enable APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  tasks.googleapis.com \
  storage.googleapis.com
```

### 2. Supabase Project

1. Go to https://supabase.com
2. Create new project
3. Get Project URL and service key
4. **Important**: Disable Supabase Auth (we use WorkOS)

### 3. WorkOS Application

1. Go to https://dashboard.workos.com
2. Create new application (AuthKit)
3. Configure redirect URLs
4. Enable identity providers
5. Note Client ID and Audience

### 4. PayHere Account (for Sri Lanka)

1. Go to https://payhere.lk
2. Create merchant account
3. Get Merchant ID and Secret
4. Add domain for approval

### 5. Z.AI API Key (for GLM Models)

The SDK Worker uses GLM-4.7 via Z.AI's Anthropic-compatible endpoint for cost-effective AI analysis.

1. Go to https://z.ai/model-api
2. Register or login to your account
3. Create an API Key in the [API Keys](https://z.ai/manage-apikey/apikey-list) management page
4. Copy your API Key for use in deployment

**Reference**: [Z.AI Documentation](https://docs.z.ai/llms.txt)

## Deployment Steps

### Step 0: Setup Secret Manager (One-time)

Store sensitive API keys in Google Secret Manager for secure access:

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secret for Z.AI API key
echo -n "your-zai-api-key" | gcloud secrets create zai-api-key --data-file=-

# Grant Cloud Run service account access to the secret
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding zai-api-key \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 1: Deploy Cloud Run Services

```bash
# Build and deploy gateway
# Note: Use Secret Manager for sensitive values (SUPABASE_SERVICE_KEY, etc.)
gcloud run deploy seo-pro-gateway \
  --source ./deploy/Dockerfile.gateway \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,FRONTEND_URL=https://your-frontend.vercel.app" \
  --set-secrets "SUPABASE_SERVICE_KEY=supabase-service-key:latest" \
  --set-secrets "WORKOS_CLIENT_ID=workos-client-id:latest" \
  --min-instances 0

# Build and deploy SDK worker (unified - handles all analysis)
# Uses GLM-4.7 via Z.AI's Anthropic-compatible endpoint
gcloud run deploy seo-pro-sdk-worker \
  --source ./deploy/Dockerfile.sdk-worker \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0 \
  --set-env-vars "ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic" \
  --set-env-vars "API_TIMEOUT_MS=3000000" \
  --set-env-vars "ANTHROPIC_DEFAULT_SONNET_MODEL=glm-4.7" \
  --set-secrets "ANTHROPIC_AUTH_TOKEN=zai-api-key:latest"
```

### Step 2: Create Cloud Tasks Queue

```bash
gcloud tasks queues create sdk-worker-queue \
  --project=seo-pro-production \
  --location=us-central1 \
  --max-dispatches-per-second=100 \
  --max-attempts=3 \
  --max-concurrent-dispatches=50
```

### Step 3: Deploy Supabase Migrations

```bash
# Apply migrations
psql $DATABASE_URL < supabase/migrations/001_initial_schema.sql
```

### Step 4: Deploy Frontend to Vercel

```bash
cd frontend

# Install dependencies
npm install

# Deploy to Vercel
vercel --prod
```

### Step 5: Update Environment Variables

Update `.env` with deployed service URLs:
- `SDK_WORKER_URL`
- `FRONTEND_URL`
- `API_URL`

## Environment Variables Reference

### SDK Worker (GLM Configuration)

| Variable | Value | Purpose |
|----------|-------|---------|
| `ANTHROPIC_AUTH_TOKEN` | *(from Secret Manager)* | Z.AI API key for authentication |
| `ANTHROPIC_BASE_URL` | `https://api.z.ai/api/anthropic` | Routes SDK calls to Z.AI endpoint |
| `API_TIMEOUT_MS` | `3000000` | Extended timeout for long SEO analysis |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `glm-4.7` | GLM model for Sonnet-tier requests |

### Gateway Service

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `WORKOS_CLIENT_ID` | WorkOS application client ID |
| `WORKOS_AUDIENCE` | JWT validation audience |
| `PAYHERE_MERCHANT_ID` | PayHere merchant ID |
| `PAYHERE_MERCHANT_SECRET` | PayHere merchant secret |
| `SDK_WORKER_URL` | URL of the deployed SDK Worker |
| `FRONTEND_URL` | Frontend URL for CORS |

## Post-Deployment Checklist

- [ ] All services respond to health checks
- [ ] WorkOS auth flow works end-to-end
- [ ] User sync to Supabase works
- [ ] Credit purchase flow works (PayHere)
- [ ] Audit estimation works
- [ ] Audit execution completes
- [ ] Results display correctly
- [ ] GLM routing verified (check logs show `api.z.ai` requests)

## Cost Monitoring

```bash
# View Cloud Run costs
gcloud billing budgets list

# View current usage
gcloud run services list
```

## Troubleshooting

### Health Checks

```bash
# Gateway
curl https://gateway-url.run.app/api/v1/health

# SDK Worker
curl https://sdk-worker-url.run.app/health
```

### Logs

```bash
# View logs
gcloud run services logs seo-pro-gateway --follow
gcloud run services logs seo-pro-sdk-worker --follow
```

### Verify GLM Routing

Check that SDK Worker is using Z.AI endpoint:

```bash
# Check environment variables are set
gcloud run services describe seo-pro-sdk-worker \
  --platform managed \
  --region us-central1 \
  --format='value(spec.template.spec.containers[0].env)'

# Check logs for API calls (should show api.z.ai, not api.anthropic.com)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=seo-pro-sdk-worker" \
  --limit 50 \
  --format='table(timestamp, textPayload)'
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `401 Unauthorized` | Verify Z.AI API key is valid and not expired |
| `404 Not Found` | Check `ANTHROPIC_BASE_URL` is set correctly |
| Timeout errors | Increase `API_TIMEOUT_MS` or reduce analysis scope |
| Secret not found | Verify secret name matches and service account has access |
