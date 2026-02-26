# Rate Limiting

This document covers the rate limiting implementation and how to scale it with Redis when needed.

## Overview

The API uses a **dual-layer rate limiting system**:

1. **Redis** (primary) - Distributed rate limiting across multiple instances
2. **In-Memory** (fallback) - Local rate limiting when Redis is unavailable

The system automatically falls back to in-memory rate limiting if Redis is not configured or becomes unavailable.

## Current Setup (In-Memory)

By default, the application uses in-memory rate limiting. **No configuration required.**

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| Default | 100 requests/minute |
| Audit Estimate | 10 requests/minute |
| Audit Run | 30 requests/minute |
| Credit Purchase | 5 requests/minute |
| Webhook | 10 requests/minute |

### Response Headers

The API returns rate limit information in response headers:

- `X-RateLimit-Limit` - Total requests allowed
- `X-RateLimit-Remaining` - Requests remaining in current window
- `Retry-After` - Seconds until rate limit resets (when limited)

## When to Add Redis

In-memory rate limiting works well for single-instance deployments. Consider adding Redis when:

- **Multiple Cloud Run instances** are running concurrently
- **50+ concurrent users** are regularly hitting the API
- You notice rate limits being bypassed due to instance scaling

### The Scaling Problem

Cloud Run auto-scales based on traffic. Each instance has its own in-memory rate limit counter:

```
Rate limit: 10 requests/minute
Instances: 3 containers
Effective limit: ~30 requests/minute (user could hit each instance)
```

For most SaaS apps starting out, this is acceptable. Add Redis when you need consistent rate limiting across all instances.

## Adding Redis

### Step 1: Choose a Provider

#### Upstash (Recommended for Serverless)

Free tier available, designed for serverless platforms like Cloud Run.

1. Create account at [upstash.com](https://upstash.com)
2. Create a new Redis database
3. Copy the Redis URL from dashboard

```
REDIS_URL=redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:6379
```

#### Google Cloud Memorystore

If you're already on GCP, use Memorystore for fully managed Redis.

1. Enable Memorystore API in GCP
2. Create Redis instance (Basic tier, 1GB)
3. Use the instance IP in your connection string

```
REDIS_URL=redis://:YOUR_AUTH_STRING@YOUR_INSTANCE_IP:6379
```

**Note**: Memorystore requires VPC peering with Cloud Run.

#### Self-Hosted (Development)

For local development with Docker:

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

```
REDIS_URL=redis://localhost:6379/0
```

### Step 2: Add Redis Dependency

Add to `requirements.txt`:

```
redis>=5.0.0
```

### Step 3: Set Environment Variable

Add `REDIS_URL` to your environment:

**Local**: Add to `.env`
```
REDIS_URL=redis://localhost:6379/0
```

**Cloud Run**: Set in `cloudbuild.yaml` or via GCP Console

### Step 4: Deploy

Deploy your application. The rate limiter will automatically detect and use Redis.

## Verifying Redis is Working

### Check Logs

Look for Redis connection logs on startup. If Redis connects successfully, you'll see it being used for rate limiting.

### Test Rate Limiting

```bash
# Make multiple requests quickly
for i in {1..15}; do
  curl -X POST https://your-api.com/audit/estimate \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com"}' \
    -w "\nStatus: %{http_code}\n\n"
done
```

You should see `429 Too Many Requests` after hitting the limit, with consistent behavior regardless of instance count.

## Implementation Details

The rate limiter is implemented in `api/rate_limiter.py`:

- Uses `redis.asyncio` for async Redis operations
- Atomic operations with `SET nx=True ex=60` to prevent race conditions
- Key format: `rate_limit:{identifier}:{endpoint}`
- Thread-safe in-memory fallback with `asyncio.Lock()`

### Applying Rate Limits to Endpoints

Use the `@rate_limit` decorator on endpoints:

```python
from api.rate_limiter import rate_limit

@rate_limit(endpoint="audit_estimate", limit=10)
async def estimate_audit(request: Request):
    # endpoint logic
    pass
```
