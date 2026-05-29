#!/bin/bash
set -euo pipefail

# Claude API Docs Installer v1.0
# Installs claude-api-docs to ~/.claude-api-docs

echo "Claude API Docs Installer v1.0"
echo "=============================="

INSTALL_DIR="$HOME/.claude-api-docs"
INSTALL_BRANCH="main"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    echo "✓ Detected macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
    echo "✓ Detected Linux"
else
    echo "❌ Error: Unsupported OS type: $OSTYPE"
    echo "This installer supports macOS and Linux only"
    exit 1
fi

# Check dependencies
echo "Checking dependencies..."
for cmd in git jq curl; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "❌ Error: $cmd is required but not installed"
        exit 1
    fi
done
echo "✓ All dependencies satisfied"

# Determine source: GitHub repo or local directory
# If run from the repo directory itself, use local copy
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GITHUB_REPO_URL="https://github.com/YOUR_USERNAME/claude-api-docs.git"

echo ""

# Install or update
if [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/docs/docs_manifest.json" ]]; then
    echo "✓ Found existing installation at ~/.claude-api-docs"
    echo "  Updating to latest version..."

    cd "$INSTALL_DIR"
    local_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

    # Check if remote is configured
    if git remote get-url origin >/dev/null 2>&1; then
        git pull --quiet origin "$local_branch" 2>/dev/null || {
            echo "  ⚠️  Could not pull from remote (offline?)"
        }
    else
        echo "  ℹ️  No remote configured - skipping pull"
    fi
else
    echo "No existing installation found"

    # Check if we're running from the repo directory
    if [[ -f "$SCRIPT_DIR/scripts/fetch_claude_api_docs.py" ]]; then
        echo "Installing from local directory: $SCRIPT_DIR"
        if [[ "$SCRIPT_DIR" != "$INSTALL_DIR" ]]; then
            cp -r "$SCRIPT_DIR" "$INSTALL_DIR"
            echo "✓ Copied to $INSTALL_DIR"
        fi
    else
        echo "Cloning from GitHub..."
        if [[ "$GITHUB_REPO_URL" == *"YOUR_USERNAME"* ]]; then
            echo "⚠️  GitHub repository URL not configured."
            echo "   Edit install.sh and set GITHUB_REPO_URL, or run from the repo directory."
            echo ""
            echo "   Alternatively, copy this folder to ~/.claude-api-docs manually:"
            echo "   cp -r \"$SCRIPT_DIR\" \"$INSTALL_DIR\""
            exit 1
        fi
        git clone -b "$INSTALL_BRANCH" "$GITHUB_REPO_URL" "$INSTALL_DIR"
    fi
fi

cd "$INSTALL_DIR"

echo ""
echo "Setting up Claude API Docs v1.0..."

# Install helper script from template
echo "Installing helper script..."
if [[ -f "$INSTALL_DIR/scripts/claude-api-docs-helper.sh.template" ]]; then
    cp "$INSTALL_DIR/scripts/claude-api-docs-helper.sh.template" "$INSTALL_DIR/claude-api-docs-helper.sh"
    chmod +x "$INSTALL_DIR/claude-api-docs-helper.sh"
    echo "✓ Helper script installed"
else
    echo "❌ Template file missing"
    exit 1
fi

# Set up /api-docs command
echo "Setting up /api-docs command..."
mkdir -p ~/.claude/commands

cat > ~/.claude/commands/api-docs.md << 'EOF'
Execute the Claude API Docs helper script at ~/.claude-api-docs/claude-api-docs-helper.sh

Usage:
- /api-docs - List all available documentation topics
- /api-docs <topic> - Read specific documentation
- /api-docs -t - Check sync status
- /api-docs -t <topic> - Check freshness then read documentation
- /api-docs whats new - Show recent documentation changes

Topic naming: subdirectories use __ separator
Examples:
  /api-docs get-started
  /api-docs about-claude__models__overview
  /api-docs build-with-claude__prompt-caching
  /api-docs agents-and-tools__tool-use__overview
  /api-docs mcp__overview
  /api-docs managed-agents__overview

Execute: ~/.claude-api-docs/claude-api-docs-helper.sh "$ARGUMENTS"
EOF

echo "✓ Created /api-docs command"

# Set up auto-update hook
echo "Setting up automatic updates..."
HOOK_COMMAND="~/.claude-api-docs/claude-api-docs-helper.sh hook-check"

if [ -f ~/.claude/settings.json ]; then
    echo "  Updating Claude settings..."
    jq '.hooks.PreToolUse = [(.hooks.PreToolUse // [])[] | select(.hooks[0].command | contains("claude-api-docs") | not)]' ~/.claude/settings.json > ~/.claude/settings.json.tmp

    jq --arg cmd "$HOOK_COMMAND" '.hooks.PreToolUse = [(.hooks.PreToolUse // [])[]] + [{"matcher": "Read", "hooks": [{"type": "command", "command": $cmd}]}]' ~/.claude/settings.json.tmp > ~/.claude/settings.json
    rm -f ~/.claude/settings.json.tmp
    echo "✓ Updated Claude settings"
else
    echo "  Creating Claude settings..."
    jq -n --arg cmd "$HOOK_COMMAND" '{
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Read",
                    "hooks": [{"type": "command", "command": $cmd}]
                }
            ]
        }
    }' > ~/.claude/settings.json
    echo "✓ Created Claude settings"
fi

echo ""
echo "✅ Claude API Docs v1.0 installed successfully!"
echo ""
echo "📚 Command: /api-docs"
echo "📂 Location: ~/.claude-api-docs"
echo ""
echo "Usage examples:"
echo "  /api-docs get-started"
echo "  /api-docs about-claude__models__overview"
echo "  /api-docs build-with-claude__prompt-caching"
echo "  /api-docs agents-and-tools__tool-use__overview"
echo ""

if [[ -f "$INSTALL_DIR/docs/docs_manifest.json" ]]; then
    echo "Available topics:"
    ls "$INSTALL_DIR/docs" | grep '\.md$' | sed 's/\.md$//' | sort | column -c 60
else
    echo "ℹ️  No docs fetched yet. Run the fetch script to download documentation:"
    echo "  cd ~/.claude-api-docs && pip install -r scripts/requirements.txt && python3 scripts/fetch_claude_api_docs.py"
fi

echo ""
echo "⚠️  Note: Restart Claude Code for the /api-docs command to take effect"
