# Claude API Documentation Mirror

Local mirror of Claude API documentation from https://platform.claude.com/docs/en/home, updated every 6 hours via GitHub Actions.

## Why This Exists

- **Faster access** — Reads from local files instead of fetching from the web
- **Automatic updates** — Stays current with the latest documentation
- **Claude Code integration** — `/api-docs` slash command for instant access

## Covered Sections (121 pages)

| Section | Topics |
|---------|--------|
| get-started | Quickstart, API keys |
| intro | Overview, introduction |
| build-with-claude | Prompt caching, batch, streaming, extended thinking, files, citations, vision, token counting |
| agents-and-tools | Tool use, computer use, web search, code execution, MCP tunnels, agent skills |
| managed-agents | Agent setup, sessions, skills, memory stores, vaults, webhooks |
| manage-claude | Authentication, workspaces, compliance API, usage & rate limit APIs |
| test-and-evaluate | Guardrails, safety |

## Installation

### From local directory (recommended for first use)

```bash
cd /path/to/claude-api-docs
bash install.sh
```

### From GitHub (after pushing to your own repo)

Edit `install.sh` and set `GITHUB_REPO_URL`, then:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-api-docs/main/install.sh | bash
```

Then fetch the docs:

```bash
cd ~/.claude-api-docs
pip install -r scripts/requirements.txt
python3 scripts/fetch_claude_api_docs.py
```

## Usage

```bash
/api-docs                                    # List all topics
/api-docs get-started                        # Quickstart guide
/api-docs about-claude__models__overview     # Models & pricing
/api-docs build-with-claude__prompt-caching  # Prompt caching
/api-docs agents-and-tools__tool-use__overview  # Tool use
/api-docs mcp__overview                      # MCP overview
/api-docs -t                                 # Check sync status
/api-docs whats new                          # Recent changes
```

## Topic Naming

File names use `__` (double underscore) as directory separator:

| URL | Topic name |
|-----|-----------|
| `/docs/en/get-started` | `get-started` |
| `/docs/en/about-claude/models/overview` | `about-claude__models__overview` |
| `/docs/en/build-with-claude/prompt-caching` | `build-with-claude__prompt-caching` |

## Uninstall

```bash
~/.claude-api-docs/uninstall.sh
```

## Platform Compatibility

- macOS: ✅
- Linux: ✅
- Windows: ❌ (not yet supported)

## Prerequisites

- git
- jq
- curl
- Python 3.8+ (for fetch script)
- Claude Code
