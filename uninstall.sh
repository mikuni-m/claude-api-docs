#!/bin/bash
set -euo pipefail

# Claude API Documentation Mirror - Uninstaller

echo "Claude API Documentation Mirror - Uninstaller"
echo "=============================================="
echo ""

echo "This will remove:"
echo "  • The /api-docs command from ~/.claude/commands/api-docs.md"
echo "  • All claude-api-docs hooks from ~/.claude/settings.json"
echo "  • The installation directory ~/.claude-api-docs"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Remove command file
if [[ -f ~/.claude/commands/api-docs.md ]]; then
    rm -f ~/.claude/commands/api-docs.md
    echo "✓ Removed /api-docs command"
fi

# Remove hooks
if [[ -f ~/.claude/settings.json ]]; then
    cp ~/.claude/settings.json ~/.claude/settings.json.backup

    jq '.hooks.PreToolUse = [(.hooks.PreToolUse // [])[] | select(.hooks[0].command | contains("claude-api-docs") | not)]' ~/.claude/settings.json > ~/.claude/settings.json.tmp

    jq 'if .hooks.PreToolUse == [] then .hooks |= if . == {PreToolUse: []} then {} else del(.PreToolUse) end else . end | if .hooks == {} then del(.hooks) else . end' ~/.claude/settings.json.tmp > ~/.claude/settings.json.tmp2

    mv ~/.claude/settings.json.tmp2 ~/.claude/settings.json
    rm -f ~/.claude/settings.json.tmp
    echo "✓ Removed hooks (backup: ~/.claude/settings.json.backup)"
fi

# Remove installation directory
INSTALL_DIR="$HOME/.claude-api-docs"
if [[ -d "$INSTALL_DIR" ]]; then
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        cd "$INSTALL_DIR"
        if [[ -z "$(git status --porcelain 2>/dev/null)" ]]; then
            cd "$HOME"
            rm -rf "$INSTALL_DIR"
            echo "✓ Removed $INSTALL_DIR"
        else
            echo "⚠️  Preserved $INSTALL_DIR (has uncommitted changes)"
        fi
    else
        rm -rf "$INSTALL_DIR"
        echo "✓ Removed $INSTALL_DIR"
    fi
fi

echo ""
echo "✅ Uninstall complete!"
