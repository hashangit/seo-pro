# SEO Pro - Developer Guide

This guide covers the development workflow, branching strategy, and engineering standards for the SEO Pro project.

---

## Branching Strategy

We follow a three-tier branching model to ensure stable production deployments while enabling rapid iteration.

```
┌─────────────────────────────────────────────────────────────────┐
│                         BRANCH FLOW                              │
└─────────────────────────────────────────────────────────────────┘

  main-dev ───────────────────────────────────────────────►
      │                                                    ▲
      │ feature/xxx                                         │
      ├──────────► feature/hashangit/add-oauth ────────────┤
      │                (dev QA)                             │
      │                                                    │
      │                                                    │
      │ merge after dev QA                                 │
      │                                                    │
      ▼                                                    │
  stage-1 ◄────────────────────────────────────────────────┤
      │                                                    │
      │ testing & UAT                                      │
      │                                                    │
      ▼                                                    │
  main ◄────────────────────────────────────────────────────┘
      │
      │ deploy to production
      ▼
  LIVE
```

### Branch Overview

| Branch | Purpose | Protection | Deploy Target |
|--------|---------|------------|---------------|
| `main` | Production code only | Protected, no direct commits | Production |
| `stage-1` | Testing & UAT | Protected, PR required | Staging/Preview |
| `main-dev` | Active development | Protected, PR required | Development |

### Branch Rules

#### `main` (Production)
- **Never commit directly** — reserved for production-ready code only
- Merges only from `stage-1` after UAT sign-off
- Every merge triggers a production deployment
- Tagged releases are created from this branch

#### `stage-1` (Staging/UAT)
- Primary preview and testing branch
- Merges from `main-dev` after dev QA passes
- Used for UAT, integration testing, and stakeholder review
- Deploys to staging environment automatically

#### `main-dev` (Development)
- Primary development branch
- **Create feature branches from this branch**
- Merge feature branches back here after dev QA
- Fast-moving; may contain work-in-progress code

### Feature Branches

**Naming Convention:**
```
{type}/{author}/{description}
```

| Type | Description |
|------|-------------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring |
| `docs/` | Documentation changes |
| `chore/` | Maintenance tasks |

**Examples:**
- `feature/hashangit/add-oauth`
- `fix/hashangit/credit-calculation`
- `refactor/hashangit/sdk-worker`

### Workflow

1. **Start Feature**
   ```bash
   git checkout main-dev
   git pull origin main-dev
   git checkout -b feature/hashangit/my-feature
   ```

2. **Develop & Commit**
   ```bash
   # Make changes
   git add .
   git commit -m "feat: add new analysis type"
   ```

3. **Dev QA**
   - Run tests locally
   - Verify functionality
   - Self-review code

4. **Create PR to `main-dev`**
   ```bash
   git push origin feature/hashangit/my-feature
   gh pr create --base main-dev
   ```

5. **After PR Approval → Merge to `main-dev`**

6. **Merge to `stage-1` for UAT**
   ```bash
   git checkout stage-1
   git merge main-dev
   git push origin stage-1
   ```

7. **After UAT Sign-off → Merge to `main`**
   ```bash
   git checkout main
   git merge stage-1
   git push origin main
   # Production deployment triggers automatically
   ```

---

## Engineering Standards

### Code Style

#### Python (Backend)
- **Formatter:** Ruff (replaces Black, isort, flake8)
- **Type hints:** Required for all function signatures
- **Docstrings:** Google style for public functions/classes
- **Line length:** 100 characters max

```python
# Good
def analyze_page(url: str, analysis_types: list[str]) -> AnalysisResult:
    """Analyze a page for SEO issues.

    Args:
        url: The URL to analyze.
        analysis_types: List of analysis types to run.

    Returns:
        AnalysisResult with scores and recommendations.
    """
    ...
```

#### TypeScript (Frontend)
- **Formatter:** Prettier
- **Linter:** ESLint with Next.js config
- **Type safety:** Strict mode enabled, no `any` types
- **Imports:** Absolute imports via `@/` alias

```typescript
// Good
interface AnalysisProps {
  url: string;
  types: AnalysisType[];
}

export function AnalysisCard({ url, types }: AnalysisProps) {
  // ...
}
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |
| `chore` | Maintenance |

**Examples:**
```
feat(credits): add PayHere payment integration
fix(gateway): resolve timeout on long-running audits
docs(api): update OpenAPI spec for new endpoints
```

### Testing Requirements

| Component | Requirement |
|-----------|-------------|
| API Endpoints | Unit tests for all routes |
| Workers | Integration tests for analysis flow |
| Frontend | Component tests for UI elements |
| Critical Paths | E2E tests for payment/auth flows |

**Before merging:**
```bash
# Run all tests
pytest
npm test --prefix frontend

# Check coverage
pytest --cov=api --cov=workers
```

### Code Review Standards

**All PRs require:**
- [ ] Tests pass locally and in CI
- [ ] No regressions in existing functionality
- [ ] Documentation updated for API changes
- [ ] Type hints/docstrings for new functions
- [ ] No hardcoded secrets or credentials

**Review checklist:**
- [ ] Code follows project style guide
- [ ] Error handling is appropriate
- [ ] No security vulnerabilities
- [ ] Performance implications considered
- [ ] Backwards compatibility maintained

### Security Standards

1. **Never commit secrets** — Use environment variables
2. **Validate all inputs** — Especially URLs and user data
3. **Use parameterized queries** — Prevent SQL injection
4. **Sanitize outputs** — Prevent XSS
5. **Check permissions** — Verify user access before operations
6. **Log responsibly** — No PII or secrets in logs

### Error Handling

```python
# Good: Specific exceptions with context
try:
    result = await run_analysis(url)
except TimeoutError:
    raise AnalysisTimeoutError(f"Analysis timed out for {url}")
except httpx.HTTPStatusError as e:
    raise UpstreamError(f"Upstream service error: {e.response.status_code}")
```

### Logging

```python
import structlog

logger = structlog.get_logger()

# Good: Structured logging with context
logger.info("analysis_started", url=url, types=analysis_types)
logger.error("analysis_failed", url=url, error=str(e), exc_info=True)
```

---

## Development Environment

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop
- Git

### Setup
```bash
# Clone and setup
git clone https://github.com/hashangit/seo-pro.git
cd seo-pro
cp .env.example .env

# Start services
docker-compose up -d
```

### Useful Commands
```bash
# Run tests
pytest
npm test --prefix frontend

# Lint code
ruff check .
npm run lint --prefix frontend

# Format code
ruff format .
npm run format --prefix frontend

# Type check
mypy api workers
npm run type-check --prefix frontend
```

---

*Last updated: February 2026*
