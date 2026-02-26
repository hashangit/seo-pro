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

## Deployment Steps

### Step 1: Deploy Cloud Run Services

```bash
# Build and deploy gateway
gcloud run deploy seo-pro-gateway \
  --source ./deploy/Dockerfile.gateway \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "$(cat .env | grep -v '^#' | xargs)" \
  --min-instances 0

# Build and deploy SDK worker (unified - handles all analysis)
gcloud run deploy seo-pro-sdk-worker \
  --source ./deploy/Dockerfile.sdk-worker \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0
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

## Post-Deployment Checklist

- [ ] All services respond to health checks
- [ ] WorkOS auth flow works end-to-end
- [ ] User sync to Supabase works
- [ ] Credit purchase flow works (PayHere)
- [ ] Audit estimation works
- [ ] Audit execution completes
- [ ] Results display correctly

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
