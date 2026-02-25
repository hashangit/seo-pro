#!/usr/bin/env bash
set -euo pipefail

# SEO Pro Installer
# Wraps everything in main() to prevent partial execution on network failure

main() {
    SKILL_DIR="${HOME}/.claude/skills/seo"
    AGENT_DIR="${HOME}/.claude/agents"
    REPO_URL="https://github.com/hashangit/seo-pro"

    echo "════════════════════════════════════════"
    echo "║   SEO Pro - Installer                ║"
    echo "║   SEO Pro Skill for Claude Code      ║"
    echo "════════════════════════════════════════"
    echo ""

    # Check prerequisites
    command -v python3 >/dev/null 2>&1 || { echo "✗ Python 3 is required but not installed."; exit 1; }
    command -v git >/dev/null 2>&1 || { echo "✗ Git is required but not installed."; exit 1; }

    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "✓ Python ${PYTHON_VERSION} detected"

    # Create directories
    mkdir -p "${SKILL_DIR}"
    mkdir -p "${AGENT_DIR}"

    # Clone or update
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf ${TEMP_DIR}" EXIT

    echo "↓ Downloading SEO Pro..."
    git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/seo-pro" 2>/dev/null

    # Copy skill files
    echo "→ Installing skill files..."
    cp -r "${TEMP_DIR}/seo-pro/seo/"* "${SKILL_DIR}/"

    # Copy sub-skills
    if [ -d "${TEMP_DIR}/seo-pro/skills" ]; then
        for skill_dir in "${TEMP_DIR}/seo-pro/skills"/*/; do
            skill_name=$(basename "${skill_dir}")
            target="${HOME}/.claude/skills/${skill_name}"
            mkdir -p "${target}"
            cp -r "${skill_dir}"* "${target}/"
        done
    fi

    # Copy schema templates
    if [ -d "${TEMP_DIR}/seo-pro/schema" ]; then
        mkdir -p "${SKILL_DIR}/schema"
        cp -r "${TEMP_DIR}/seo-pro/schema/"* "${SKILL_DIR}/schema/"
    fi

    # Copy reference docs
    if [ -d "${TEMP_DIR}/seo-pro/pdf" ]; then
        mkdir -p "${SKILL_DIR}/pdf"
        cp -r "${TEMP_DIR}/seo-pro/pdf/"* "${SKILL_DIR}/pdf/"
    fi

    # Copy agents
    echo "→ Installing subagents..."
    cp -r "${TEMP_DIR}/seo-pro/agents/"*.md "${AGENT_DIR}/" 2>/dev/null || true

    # Copy shared scripts
    if [ -d "${TEMP_DIR}/seo-pro/scripts" ]; then
        mkdir -p "${SKILL_DIR}/scripts"
        cp -r "${TEMP_DIR}/seo-pro/scripts/"* "${SKILL_DIR}/scripts/"
    fi

    # Copy hooks
    if [ -d "${TEMP_DIR}/seo-pro/hooks" ]; then
        mkdir -p "${SKILL_DIR}/hooks"
        cp -r "${TEMP_DIR}/seo-pro/hooks/"* "${SKILL_DIR}/hooks/"
        chmod +x "${SKILL_DIR}/hooks/"*.sh 2>/dev/null || true
        chmod +x "${SKILL_DIR}/hooks/"*.py 2>/dev/null || true
    fi

    # Install Python dependencies
    echo "→ Installing Python dependencies..."
    if command -v uv >/dev/null 2>&1; then
        uv pip install -r "${TEMP_DIR}/seo-pro/requirements.txt" 2>/dev/null || \
        echo "⚠  Could not auto-install Python packages. Run: uv pip install -r requirements.txt"
    else
        pip install --quiet --break-system-packages -r "${TEMP_DIR}/seo-pro/requirements.txt" 2>/dev/null || \
        pip install --quiet -r "${TEMP_DIR}/seo-pro/requirements.txt" 2>/dev/null || \
        echo "⚠  Could not auto-install Python packages. Run: pip install -r requirements.txt"
    fi

    # Optional: Install Playwright browsers
    echo "→ Installing Playwright browsers (optional)..."
    if [ -x "${HOME}/.venv/bin/playwright" ]; then
        "${HOME}/.venv/bin/playwright" install chromium 2>/dev/null || \
        echo "⚠  Playwright browser install failed. Screenshots won't work. Run: playwright install chromium"
    else
        python3 -m playwright install chromium 2>/dev/null || \
        echo "⚠  Playwright browser install failed. Screenshots won't work. Run: playwright install chromium"
    fi

    echo ""
    echo "✓ SEO Pro installed successfully!"
    echo ""
    echo "Usage:"
    echo "  1. Start Claude Code:  claude"
    echo "  2. Run commands:       /seo audit https://example.com"
    echo ""
    echo "To uninstall: curl -fsSL https://raw.githubusercontent.com/hashangit/seo-pro/main/uninstall.sh | bash"
}

main "$@"
