# Troubleshooting

## Common Issues

### Skill Not Loading

**Symptom:** `/seo` command not recognized

**Solutions:**

1. Verify installation:
```bash
ls ~/.claude/skills/seo/SKILL.md
```

2. Check SKILL.md has proper frontmatter:
```bash
head -5 ~/.claude/skills/seo/SKILL.md
```
Should start with `---` followed by YAML.

3. Restart Claude Code:
```bash
claude
```

4. Re-run installer:
```bash
curl -fsSL https://raw.githubusercontent.com/hashangit/seo-pro/main/install.sh | bash
```

---

### Python Dependency Errors

**Symptom:** `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
pip install -r ~/.claude/skills/seo/requirements.txt
```

Or install individually:
```bash
pip install beautifulsoup4 requests lxml playwright Pillow urllib3 validators
```

---

### Playwright Screenshot Errors

**Symptom:** `playwright._impl._errors.Error: Executable doesn't exist`

**Solution:**
```bash
playwright install chromium
```

If that fails:
```bash
pip install playwright
python -m playwright install chromium
```

---

### Permission Denied Errors

**Symptom:** `Permission denied` when running scripts

**Solution:**
```bash
chmod +x ~/.claude/skills/seo/scripts/*.py
chmod +x ~/.claude/skills/seo/hooks/*.py
chmod +x ~/.claude/skills/seo/hooks/*.sh
```

---

### Hook Not Triggering

**Symptom:** Schema validation hook not running

**Check:**

1. Verify hook is in settings:
```bash
cat ~/.claude/settings.json
```

2. Ensure correct path:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/skills/seo/hooks/validate-schema.py \"$FILE_PATH\"",
            "exitCodes": { "2": "block" }
          }
        ]
      }
    ]
  }
}
```

3. Test hook directly:
```bash
python3 ~/.claude/skills/seo/hooks/validate-schema.py test.html
```

---

### Subagent Not Found

**Symptom:** `Agent 'seo-technical' not found`

**Solution:**

1. Verify agent files exist:
```bash
ls ~/.claude/agents/seo-*.md
```

2. Check agent frontmatter:
```bash
head -5 ~/.claude/agents/seo-technical.md
```

3. Re-install agents:
```bash
cp /path/to/seo-pro/agents/*.md ~/.claude/agents/
```

---

### Timeout Errors

**Symptom:** `Request timed out after 30 seconds`

**Solutions:**

1. The target site may be slow — try again
2. Increase timeout in script calls
3. Check your network connection
4. Some sites block automated requests

---

### Schema Validation False Positives

**Symptom:** Hook blocks valid schema

**Check:**

1. Ensure placeholders are replaced
2. Verify @context is `https://schema.org`
3. Check for deprecated types (HowTo, SpecialAnnouncement)
4. Validate at [Google's Rich Results Test](https://search.google.com/test/rich-results)

---

### Slow Audit Performance

**Symptom:** Full audit takes too long

**Solutions:**

1. Audit crawls up to 500 pages — large sites take time
2. Subagents run in parallel to speed up analysis
3. For faster checks, use `/seo page` on specific URLs
4. Check if site has slow response times

---

## SaaS Platform Issues

### Backend Fails to Start

**Symptom:** Uvicorn exits with `ModuleNotFoundError` or connection refused

**Solutions:**

1. Activate the virtual environment:
```bash
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Check `.env` has required variables (see `.env.example` for current schema)

4. Check for port conflicts:
```bash
lsof -i :8080
```

---

### Auth / JWKS Errors

**Symptom:** `401 Unauthorized` or `Unable to find a valid signing key`

**Solutions:**

1. Verify `WORKOS_CLIENT_ID` is set correctly in `.env`
2. The JWKS URL is now `https://api.workos.com/sso/jwks/{client_id}` (AuthKit-specific), not the old `/v1/jwks` path
3. `WORKOS_AUDIENCE` is optional — leave blank unless you configured a custom audience claim in WorkOS
4. `WORKOS_ISSUER` has been removed — AuthKit uses client-specific issuers
5. If keys change, the backend automatically refreshes the JWKS cache on the next request

---

### WebSocket Connection Failures

**Symptom:** Real-time audit status not updating, WebSocket errors in console

**Solutions:**

1. Check that `SUPABASE_DATABASE_URL` is set (direct Postgres connection for LISTEN/NOTIFY)
2. Verify the database has the LISTEN/NOTIFY trigger installed (in `001_initial_schema.sql`)
3. Check backend logs for `pg_pool_init_failed` — this is expected if no direct DB URL is configured (REST API still works)
4. Verify the frontend WebSocket URL points to the correct backend address

---

### Frontend Build / Compile Errors

**Symptom:** Next.js fails to compile or shows white screen

**Solutions:**

1. Install dependencies:
```bash
cd frontend && npm install
```

2. Clear Next.js cache:
```bash
rm -rf frontend/.next
```

3. Check Node.js version (20+ required):
```bash
node --version
```

4. Verify `.env` has `NEXT_PUBLIC_WORKOS_CLIENT_ID` and `NEXT_PUBLIC_WORKOS_REDIRECT_URI`

---

## Getting Help

1. **Check the docs:** Review [COMMANDS.md](COMMANDS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)

2. **GitHub Issues:** Report bugs at the repository

3. **Logs:** Check Claude Code's output for error details, or backend logs at `/tmp/backend.log` and frontend logs at `/tmp/frontend.log`

## Debug Mode

To see detailed output, check Claude Code's internal logs or run scripts directly:

```bash
# Test fetch
python3 ~/.claude/skills/seo/scripts/fetch_page.py https://example.com

# Test parse
python3 ~/.claude/skills/seo/scripts/parse_html.py page.html --json

# Test screenshot
python3 ~/.claude/skills/seo/scripts/capture_screenshot.py https://example.com

# Check backend logs
cat /tmp/backend.log

# Check frontend logs
cat /tmp/frontend.log
```
