# 07 — Infrastructure

## CI/CD Pipeline

### GitHub Actions (`.github/workflows/ci.yml`)

Four parallel jobs on push/PR to `main` and `develop`:

| Job | Purpose | Key Steps |
|-----|---------|-----------|
| **backend-tests** | Python validation | Ruff lint, mypy type check, pytest with coverage |
| **frontend-tests** | TypeScript validation | pnpm install, ESLint, tsc, Jest tests, Next.js build |
| **security-scan** | Vulnerability scanning | Trivy filesystem scan, SARIF upload to GitHub Security |
| **docker-build** | Image validation | Build all 3 Dockerfiles (gateway, sdk-worker, orchestrator) without push |

### Cloud Build (`cloudbuild.yaml`)

Production deployment pipeline triggered by commits:

```
1. Build gateway Docker image
2. Build SDK worker Docker image
3. Push to Artifact Registry (tagged with COMMIT_SHA + latest)
4. Deploy gateway to Cloud Run (512Mi, 100 max instances, 300s timeout)
5. Deploy SDK worker to Cloud Run (4Gi, 10 max instances, 300s timeout)
```

Machine type: `E2_HIGHCPU_8`, timeout: 30 minutes

### Standalone Build Configs

- **`cloudbuild-gateway.yaml`**: Deploys gateway with env-vars-file, sets Supabase URL, WorkOS settings, frontend origins
- **`cloudbuild-sdk-worker.yaml`**: Deploys SDK worker with Z.AI API endpoint, 4Gi memory, 600s timeout

## Deployment

### Production Environment

| Component | Hosting | Config |
|-----------|---------|--------|
| Frontend | Vercel | `frontend-tau-six-83.vercel.app` + `seopro-hashangits-projects.vercel.app` |
| Gateway | Cloud Run | `seo-pro-gateway`, us-central1, 512Mi, allow-unauthenticated |
| SDK Worker | Cloud Run | `seo-pro-sdk-worker`, us-central1, 4Gi, allow-unauthenticated |
| Database | Supabase | `cuumnoebybededepkuyi.supabase.co`, PostgreSQL 17 |
| Secrets | Secret Manager | supabase-service-key, workos-client-id, zai-api-key, sendgrid-api-key |

### Dockerfiles (3 total)

| Dockerfile | Base Image | Key Contents | Entrypoint |
|------------|------------|-------------|------------|
| `Dockerfile.gateway` | python:3.11-slim (multi-stage) | api/ + orchestrator/ | gunicorn -w 4 |
| `Dockerfile.sdk-worker` | playwright/python:v1.48.0-jammy | worker + skills + agents + scripts + playwright browsers | gunicorn -w 1 |
| `Dockerfile.orchestrator` | python:3.11-slim | scheduler.py | gunicorn -w 1 |

All three run as non-root user, expose port 8080, include health checks.

### Docker Compose (Local Dev)

Three services defined in `docker-compose.yml`:

```
gateway (8080): Dockerfile.gateway + volume mounts for live reload
http-worker (8081): Dockerfile.http-worker (legacy, not in deploy/)
frontend (3000): node:20-alpine with npm install + npm run dev
```

## Environment Configuration

Critical environment variables (from `.env.example`):

| Variable | Purpose | Required In |
|----------|---------|-------------|
| `SUPABASE_URL` | Database endpoint | All services |
| `SUPABASE_SECRET_KEY` | Service role key (bypasses RLS) | Gateway, Worker |
| `SUPABASE_PUBLISHABLE_KEY` | Anon key (client-safe) | Frontend |
| `WORKOS_CLIENT_ID` | OAuth client ID | Gateway, Frontend |
| `WORKOS_AUDIENCE` | JWT audience (`api.workos.com`) | Gateway |
| `ANTHROPIC_AUTH_TOKEN` | Z.AI API key | SDK Worker |
| `ANTHROPIC_BASE_URL` | `https://api.z.ai/api/anthropic` | SDK Worker |
| `SENDGRID_API_KEY` | Email delivery | Gateway |
| `ADMIN_EMAILS` | Comma-separated admin emails | Gateway |
| `FRONTEND_URL` | CORS origin | Gateway |
| `SDK_WORKER_URL` | Worker endpoint | Gateway |
| `DEV_MODE` | Unlimited credits (dev only) | Gateway |
| `REDIS_URL` | Optional distributed rate limit | Gateway |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Gateway |
| `QUEUE_PATH` | Cloud Tasks queue path | Gateway |

## Secret Management

Production secrets stored in **Google Cloud Secret Manager**:
- `supabase-service-key`
- `supabase-url`
- `workos-client-id`
- `workos-audience`
- `zai-api-key`
- `sendgrid-api-key`

Referenced in Cloud Build configs via `--set-secrets` flag.

## Rate Limiting Architecture

Optional Redis-based distributed rate limiting. Falls back to in-memory if `REDIS_URL` not set. Per-endpoint configuration with custom limits per route.

## Email Infrastructure

- **SendGrid** for transactional emails
- Templates: credit request confirmation, payment proof notification, approval, rejection
- Falls back to Python logging if no API key configured
- Admin emails received at addresses in `ADMIN_EMAILS`

## Third-Party SaaS Dependencies

| Service | Purpose | Critical? |
|---------|---------|-----------|
| **WorkOS** | SSO authentication, JWT issuance | Yes |
| **Supabase** | PostgreSQL hosting | Yes |
| **Z.AI** | Claude Agent SDK API provider (GLM-4.7) | Yes |
| **SendGrid** | Email delivery | Yes (for payment flow) |
| **Vercel** | Frontend hosting | Yes |
| **Google Cloud** | Compute + tasks + secrets | Yes |
| **GitHub** | Source control + CI/CD | No (recoverable) |
