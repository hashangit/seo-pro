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

    ┌─────────────┐
    │  SendGrid   │  ← Email notifications
    │  (External) │
    └─────────────┘
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
  storage.googleapis.com \
  secretmanager.googleapis.com
```

### 2. Supabase Project

1. Go to https://supabase.com
2. Create new project
3. Get Project URL and service key
4. **Important**: Disable Supabase Auth (we use WorkOS)

### 3. WorkOS Application

1. Go to https://dashboard.workos.com
2. Create new application (AuthKit)
3. Configure redirect URLs:
   - `https://your-domain.com/auth/callback`
   - `http://localhost:3000/auth/callback` (development)
4. Enable identity providers (Google, GitHub, etc.)
5. Note Client ID and Audience

### 4. Z.AI API Key (for GLM Models)

The SDK Worker uses GLM-4.7 via Z.AI's Anthropic-compatible endpoint for cost-effective AI analysis.

1. Go to https://z.ai/model-api
2. Register or login to your account
3. Create an API Key in the [API Keys](https://z.ai/manage-apikey/apikey-list) management page
4. Copy your API Key for use in deployment

**Reference**: [Z.AI Documentation](https://docs.z.ai/llms.txt)

### 5. SendGrid Account (Email Notifications)

1. Go to https://sendgrid.com
2. Create account and verify your sender domain
3. Create API Key with "Mail Send" permissions
4. Note your API key and verified sender email

## Deployment Steps

### Step 0: Setup Secret Manager (One-time)

Store sensitive API keys in Google Secret Manager for secure access:

```bash
# Enable Secret Manager API (if not already enabled)
gcloud services enable secretmanager.googleapis.com

# Get project number for service account
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

# Create secrets for all sensitive values
# Z.AI API key
echo -n "your-zai-api-key" | gcloud secrets create zai-api-key --data-file=-

# Supabase service key
echo -n "your-supabase-service-key" | gcloud secrets create supabase-service-key --data-file=-

# WorkOS client ID
echo -n "your-workos-client-id" | gcloud secrets create workos-client-id --data-file=-

# SendGrid API key
echo -n "your-sendgrid-api-key" | gcloud secrets create sendgrid-api-key --data-file=-

# Grant Cloud Run service account access to all secrets
for secret in zai-api-key supabase-service-key workos-client-id sendgrid-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

### Step 1: Deploy Cloud Run Services

```bash
# Build and deploy gateway
gcloud run deploy seo-pro-gateway \
  --source ./api \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "\
ENVIRONMENT=production,\
FRONTEND_URL=https://your-frontend.vercel.app,\
SUPABASE_URL=https://xxxxx.supabase.co,\
WORKOS_AUDIENCE=api.workos.com,\
WORKOS_ISSUER=api.workos.com,\
WORKOS_JWKS_URL=https://api.workos.com/v1/jwks,\
ADMIN_EMAILS=admin@yourdomain.com,\
SENDGRID_FROM_EMAIL=noreply@yourdomain.com,\
SENDGRID_FROM_NAME=SEO Pro" \
  --set-secrets "\
SUPABASE_SECRET_KEY=supabase-service-key:latest,\
WORKOS_CLIENT_ID=workos-client-id:latest,\
SENDGRID_API_KEY=sendgrid-api-key:latest" \
  --min-instances 0 \
  --memory 512Mi \
  --cpu 1

# Build and deploy SDK worker (unified - handles all analysis)
gcloud run deploy seo-pro-sdk-worker \
  --source ./workers \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 0 \
  --timeout 600 \
  --set-env-vars "\
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic,\
API_TIMEOUT_MS=3000000,\
ANTHROPIC_DEFAULT_SONNET_MODEL=glm-4.7" \
  --set-secrets "\
ANTHROPIC_AUTH_TOKEN=zai-api-key:latest"
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
# Get database URL from Supabase dashboard
# Then apply migrations
psql $DATABASE_URL < supabase/migrations/001_initial_schema.sql
```

### Step 4: Deploy Frontend to Vercel

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables in Vercel dashboard or CLI
vercel env add NEXT_PUBLIC_WORKOS_CLIENT_ID
vercel env add NEXT_PUBLIC_WORKOS_REDIRECT_URI
vercel env add NEXT_PUBLIC_API_URL
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

# Deploy to Vercel
vercel --prod
```

### Step 5: Update Environment Variables

After deployment, update the gateway with the correct service URLs:

```bash
gcloud run services update seo-pro-gateway \
  --region us-central1 \
  --update-env-vars "SDK_WORKER_URL=https://seo-pro-sdk-worker-xxxxx.a.run.app"
```

## Environment Variables Reference

### Gateway Service

| Variable | Source | Description |
|----------|--------|-------------|
| `ENVIRONMENT` | Plain | `production`, `staging`, or `development` |
| `FRONTEND_URL` | Plain | Frontend URL for CORS |
| `SDK_WORKER_URL` | Plain | URL of the deployed SDK Worker |
| `SUPABASE_URL` | Plain | Supabase project URL |
| `SUPABASE_SECRET_KEY` | Secret | Supabase service role key |
| `WORKOS_CLIENT_ID` | Secret | WorkOS application client ID |
| `WORKOS_AUDIENCE` | Plain | `api.workos.com` |
| `WORKOS_ISSUER` | Plain | `api.workos.com` |
| `WORKOS_JWKS_URL` | Plain | `https://api.workos.com/v1/jwks` |
| `ADMIN_EMAILS` | Plain | Comma-separated admin emails |
| `SENDGRID_API_KEY` | Secret | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | Plain | Verified sender email |
| `SENDGRID_FROM_NAME` | Plain | Display name for emails |

### SDK Worker (GLM Configuration)

| Variable | Value | Purpose |
|----------|-------|---------|
| `ANTHROPIC_AUTH_TOKEN` | *(from Secret Manager)* | Z.AI API key for authentication |
| `ANTHROPIC_BASE_URL` | `https://api.z.ai/api/anthropic` | Routes SDK calls to Z.AI endpoint |
| `API_TIMEOUT_MS` | `3000000` | Extended timeout for long SEO analysis |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `glm-4.7` | GLM model for Sonnet-tier requests |

### Frontend (Vercel)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_WORKOS_CLIENT_ID` | WorkOS client ID |
| `NEXT_PUBLIC_WORKOS_REDIRECT_URI` | Auth callback URL |
| `NEXT_PUBLIC_API_URL` | Gateway API URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase anon key |

## Manual Payment Flow

The application uses a manual credit purchase flow:

1. **User requests credits** → Email sent to user with invoice
2. **User makes payment** via Wise/Bank transfer
3. **User uploads proof** → Email sent to admin
4. **Admin approves** → Credits added, user notified

### Admin Access

Admin users (defined in `ADMIN_EMAILS`) can access:
- `/admin/credits` - View and manage credit requests
- Approve/reject requests with notes

## Post-Deployment Checklist

- [ ] All services respond to health checks
- [ ] WorkOS auth flow works end-to-end
- [ ] User sync to Supabase works
- [ ] Credit request flow works
- [ ] Email notifications are sent (check SendGrid logs)
- [ ] Admin can access `/admin/credits`
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

# View SendGrid usage
# Check SendGrid dashboard > Activity
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
# View gateway logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=seo-pro-gateway" \
  --limit 50 \
  --format='table(timestamp, textPayload)'

# View SDK worker logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=seo-pro-sdk-worker" \
  --limit 50 \
  --format='table(timestamp, textPayload)'
```

### Verify Email Configuration

```bash
# Check SendGrid environment variables
gcloud run services describe seo-pro-gateway \
  --platform managed \
  --region us-central1 \
  --format='value(spec.template.spec.containers[0].env)' \
  | grep -i sendgrid

# Test by creating a credit request and checking logs for email_sent events
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
| Emails not sending | Check `SENDGRID_API_KEY` secret and verify sender email in SendGrid |
| Admin access denied | Add email to `ADMIN_EMAILS` env var and redeploy |
| CORS errors | Verify `FRONTEND_URL` matches your Vercel deployment |

## Secret Rotation

To rotate secrets:

```bash
# Add new version of secret
echo -n "new-api-key" | gcloud secrets versions add sendgrid-api-key --data-file=-

# Redeploy to pick up new version
gcloud run services update seo-pro-gateway \
  --region us-central1 \
  --set-secrets "SENDGRID_API_KEY=sendgrid-api-key:latest"
```

## Rollback

To rollback to previous deployment:

```bash
# List revisions
gcloud run revisions list --service=seo-pro-gateway --region=us-central1

# Route traffic to previous revision
gcloud run services update-traffic seo-pro-gateway \
  --region us-central1 \
  --to-revisions=seo-pro-gateway-00001-abc=100
```
