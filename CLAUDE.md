# Claude API Documentation Mirror

This repository contains local copies of Claude API documentation from https://platform.claude.com/docs/en/

The docs are periodically updated via GitHub Actions (every 6 hours).

## For /api-docs Command

When responding to /api-docs commands:
1. Read documentation files from the docs/ directory
2. Use the manifest to know available topics
3. Topic names use `__` as separator for subdirectories

## Available Sections

- `get-started` — Quickstart guide
- `intro` — Overview and introduction
- `build-with-claude__*` — Prompt caching, batch, streaming, extended thinking, files, citations, vision
- `agents-and-tools__*` — Tool use, computer use, web search, MCP tunnels, agent skills
- `managed-agents__*` — Managed agent setup and sessions
- `manage-claude__*` — Authentication, workspaces, compliance API, usage & rate limit APIs
- `test-and-evaluate__*` — Guardrails, safety

## Files

@install.sh
@uninstall.sh
@scripts/
@docs/
