# SEO Pro - Local Development Guide

This guide will help you get the SEO Pro SaaS platform running on your local machine for development.

## Prerequisites

Before starting, ensure you have installed:

- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download](https://git-scm.com/downloads)
- **Node.js 20+** - [Download](https://nodejs.org/) (or use nvm)
- **Python 3.8+** - [Download](https://www.python.org/downloads/)

## External Services Required

You'll need accounts with these services (free tiers work):

1. **Supabase** - [Create project](https://supabase.com) (PostgreSQL database)
2. **WorkOS** - [Create app](https://dashboard.workos.com) (Authentication)

> **Note:** The app runs in `DEV_MODE=true` by default, which skips payments. You don't need to set up a payment gateway for local development.

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/hashangit/seo-pro.git
cd seo-pro
```

---

## Step 2: Set Up Supabase

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Once created, go to **Settings → API**
3. Copy these values:
   - **Project URL** → This is your `SUPABASE_URL`
   - **service_role** key (secret) → This is your `SUPABASE_SERVICE_KEY`
   - **anon** key (public) → This is your `SUPABASE_ANON_KEY`

4. **Important:** In Supabase, **disable Auth** (Authentication → Settings → Disable)
   - We use WorkOS for auth, not Supabase

---

## Step 3: Set Up WorkOS

1. Go to [dashboard.workos.com](https://dashboard.workos.com)
2. Create a new application (AuthKit type)
3. In the **SSO & Connections** tab, enable your preferred identity providers (Google, GitHub, etc.)
4. Go to **Overview** and note the **Client ID**
5. Go to **API Keys** and note the API Key (optional for local dev)

6. **Configure Redirect URL** for local development:
   - In WorkOS dashboard, go to **Redirect URLs**
   - Add: `http://localhost:3000`

---

## Step 4: Create Environment File

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# ============================================================================
# WorkOS Authentication
# ============================================================================
NEXT_PUBLIC_WORKOS_CLIENT_ID=client_01YOUR_WORKOS_CLIENT_ID
NEXT_PUBLIC_WORKOS_REDIRECT_URI=http://localhost:3000

WORKOS_AUDIENCE=api.workos.com
WORKOS_ISSUER=api.workos.com

# ============================================================================
# Supabase (Data Store Only)
# ============================================================================
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SUPABASE_ANON_KEY=eyJxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============================================================================
# Application URLs
# ============================================================================
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8080
SDK_WORKER_URL=http://localhost:8081

# ============================================================================
# Environment
# ============================================================================
ENVIRONMENT=development
DEV_MODE=true
```

> **Note:** You can leave `GOOGLE_CLOUD_PROJECT` and `PAYHERE_*` variables empty for local development.

---

## Step 5: Start All Services

Use Docker Compose to start all services:

```bash
docker-compose up -d
```

This will start:
- **Gateway API** → `http://localhost:8080`
- **SDK Worker** → `http://localhost:8081`
- **Frontend** → `http://localhost:3000`

**First run may take a few minutes** as Docker builds the images and installs dependencies.

---

## Step 6: Install Playwright Browsers (Optional)

The SDK worker uses Playwright CLI for browser automation. Install browsers:

```bash
# From project root
docker-compose exec sdk-worker playwright-cli install chromium
```

---

## Step 7: Verify Services Are Running

Check each service:

```bash
# Gateway health
curl http://localhost:8080/api/v1/health

# SDK Worker health
curl http://localhost:8081/health

# Frontend
open http://localhost:3000
```

---

## Development Workflow

### Running Services Individually

If you prefer running services outside Docker:

**Frontend (Next.js):**
```bash
cd frontend
npm install
npm run dev
# Visit http://localhost:3000
```

**API Gateway (FastAPI):**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run gateway
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

**SDK Worker:**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run SDK worker
uvicorn workers.sdk_worker:app --host 0.0.0.0 --port 8081 --reload
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f gateway
docker-compose logs -f sdk-worker
docker-compose logs -f frontend
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (reset database)
docker-compose down -v
```

---

## Troubleshooting

### Docker build fails

Make sure Docker Desktop is running and you have sufficient disk space.

### Port already in use

If ports 3000, 8080, or 8081 are occupied:

1. Edit `docker-compose.yml`
2. Change the port mappings (e.g., `"3001:3000"`)

### Frontend can't connect to API

Verify these match in your `.env`:
- `FRONTEND_URL=http://localhost:3000`
- `API_URL=http://localhost:8080`

### Authentication not working

1. Check WorkOS redirect URLs include `http://localhost:3000`
2. Verify `NEXT_PUBLIC_WORKOS_CLIENT_ID` is set in `.env`
3. Check browser console for WorkOS errors

---

## Useful Commands

```bash
# Rebuild containers after code changes
docker-compose up -d --build

# Enter a container shell
docker-compose exec gateway sh
docker-compose exec sdk-worker sh
docker-compose exec frontend sh

# Install new Python dependencies
pip install <package> && pip freeze > requirements.txt

# Install new frontend dependencies
cd frontend && npm install <package>
```

---

## Next Steps

1. Visit `http://localhost:3000`
2. Sign in using WorkOS (Google, GitHub, etc.)
3. Run an SEO audit on a test URL

---

## Project Structure

```
seo-pro/
├── .claude/           # Skills and Agents (loaded by SDK)
│   ├── skills/        # SEO skills (audit, page, schema, etc.)
│   └── agents/        # Subagents (technical, content, visual, etc.)
├── api/               # FastAPI gateway
├── workers/           # Background workers
│   └── sdk_worker.py  # Unified SDK worker
├── scripts/           # Python utilities (called via Bash)
├── frontend/          # Next.js web app
├── supabase/          # Database migrations
├── deploy/            # Dockerfiles
├── docker-compose.yml # Local development
├── config.py          # Centralized configuration
└── .env               # Environment variables (create this)
```

---

## Going to Production

For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).
