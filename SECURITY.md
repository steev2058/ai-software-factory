# SECURITY.md

## Environment & Secret Usage

This project reads sensitive values from environment variables only.
Never hardcode secrets in workflows, code, or docs.

Required for GitHub delivery automation:

- `GITHUB_PAT` → Personal Access Token
- `GITHUB_REPO` → `owner/repo`

Required for model calls:

- `OPENROUTER_API_KEY`

Recommended local setup:

1. Keep real secrets in `.env` only.
2. Keep `.env` out of git (`.gitignore` already covers it).
3. Rotate tokens immediately if exposed.

## Token Safety Rules

- Use least privilege scopes.
- For GitHub PAT, grant only what is needed (repo write for target repo).
- Never paste tokens in chat, tickets, screenshots, or logs.
- Do not print tokens in n8n execution logs.
- Revoke and regenerate token on any suspected leak.

## Workflow Security Notes

- Delivery workflow uses `GITHUB_PAT` from runtime env.
- Remote URL with token is used only during push step.
- Keep server access restricted and rotate SSH credentials periodically.
