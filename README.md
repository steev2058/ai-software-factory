# AI Software Factory

Complete starter system for an AI Software Factory with:

- Telegram bot as control interface
- n8n self-hosted via Docker
- OpenRouter as LLM provider
- Multi-agent workflow architecture
- Auto GitHub push per generated project
- Local disk workspace for projects

## Repository Structure

```text
ai-software-factory/
├── docker/
├── workflows/
│   └── n8n/
├── docs/
├── templates/
├── scripts/
├── projects/        # generated projects (gitignored)
├── .env.example
├── .gitignore
└── README.md
```

## 1) Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Git
- Telegram Bot Token
- OpenRouter API key

## 2) Configure Environment

```bash
cp .env.example .env
# then edit .env and fill real values
```

On VPS, this project uses:
- `/srv/ai-software-factory/.env`

Required minimum:
- `TELEGRAM_BOT_TOKEN`
- `OPENROUTER_API_KEY`
- `DASHBOARD_USER`
- `DASHBOARD_PASS`
- `N8N_WEBHOOK_URL` (default: `http://asf-n8n:5678/webhook/run-project`)

## 3) Start Services (Docker)

Run all services (postgres + n8n + dashboard):

```bash
cd docker
docker compose up -d --build
```

- n8n UI: `http://localhost:5678`
- Factory Dashboard (protected by Basic Auth): `http://localhost:5680/dashboard`

## 4) Import n8n Workflows

Workflows are under:

```text
workflows/n8n/
```

Import from n8n UI and set required credentials/env (`OPENROUTER_API_KEY`, `GITHUB_PAT`, `GITHUB_REPO`, Telegram credentials).

## 5) Multi-Agent Pattern (recommended)

Use a coordinator + specialists:

- **Coordinator Agent**: receives Telegram command and creates plan
- **Builder Agent**: generates code into `projects/<project-name>`
- **Reviewer Agent**: runs checks/lint/tests
- **Release Agent**: commits and pushes to GitHub

## 6) GitHub Auto-Push Strategy

Each generated project should:

1. Create folder in `projects/<name>`
2. Initialize git inside project
3. Add remote from your org/user
4. Commit scaffold + generated code
5. Push to `main`

Example script location:

```text
scripts/
```

## 7) Telegram Bot Interface

Telegram bot receives high-level commands like:

- `/new`
- `/spec <requirements>`
- `/run <project_id>`

Bot triggers n8n workflows, which fan out work across agents.

## 8) Factory Dashboard Usage

Open: `http://localhost:5680/dashboard`

Authentication:
- All dashboard routes are behind HTTP Basic Auth via nginx proxy.
- App middleware also enforces the same credentials (`DASHBOARD_USER` / `DASHBOARD_PASS`).

Set credentials in:
- `/srv/ai-software-factory/.env`

Example:
```env
DASHBOARD_USER=admin
DASHBOARD_PASS=replace_with_strong_password
```

Password rotation:
```bash
# edit credentials
nano /srv/ai-software-factory/.env

# restart proxy + dashboard
cd /srv/ai-software-factory/docker
docker compose up -d --build dashboard asf-dashboard-proxy
```

Features:

- Lists projects from disk (`/srv/ai-software-factory/projects`)
- Computed status per project (`NEW`, `SPEC_READY`, `RUNNING`, `PASSED`, `FAILED`, `UNKNOWN`)
- Search + status filter
- Auto refresh (8s) + manual refresh
- Project actions from UI:
  - Run project
  - Re-run project (cleans `repo/` + `logs/`, keeps spec/tasks)
  - Delete project (with confirmation)
- Project details page (`/projects/<id>`) with:
  - spec summary
  - logs list + log viewer
  - GitHub branch link (`deliver/<project_id>`) and copy button
  - ZIP path + download endpoint (`/api/projects/:id/zip`)

## Next Suggested Files

- `docker/docker-compose.yml`
- `scripts/bootstrap_project.sh`
- `scripts/push_project.sh`
- `docs/architecture.md`
- `workflows/n8n/factory-main.json`

---

If you want, I can generate the full Docker + n8n workflow + bot starter code in the next step.

## Autonomous 6-Agent Revenue System

Runner:
- `agents/revenue_system.py`

n8n workflows created:
- `workflows/n8n/agent-niche-research.workflow.json`
- `workflows/n8n/agent-analytics.workflow.json`
- `workflows/n8n/agent-optimization.workflow.json`
- `workflows/n8n/agent-revenue-report.workflow.json`

Output directories:
- `research/ideas-YYYY-MM-DD.json`
- `research/build-queue.json`
- `reports/metrics-YYYY-MM-DD.json`
- `reports/optimization-YYYY-MM-DD.json`
- `reports/revenue-YYYY-MM-DD.md`
- `reports/agent-actions.jsonl`

Manual test commands:
```bash
python3 agents/revenue_system.py niche-research
python3 agents/revenue_system.py product-builder
python3 agents/revenue_system.py marketing --project-id <project_id>
python3 agents/revenue_system.py analytics
python3 agents/revenue_system.py optimization
python3 agents/revenue_system.py revenue
python3 agents/revenue_system.py full-cycle-demo
```
