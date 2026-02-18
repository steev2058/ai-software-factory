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

Required minimum:
- `TELEGRAM_BOT_TOKEN`
- `OPENROUTER_API_KEY`

## 3) Start n8n (Docker)

Create `docker/docker-compose.yml` (or use your own stack) and run:

```bash
cd docker
docker compose up -d
```

n8n default UI: `http://localhost:5678`

## 4) Import n8n Workflows

Put workflow JSON files inside:

```text
workflows/n8n/
```

Then import them from n8n UI.

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

- `new project: ecommerce landing page`
- `update project: add auth`
- `ship project: <name>`

Bot triggers n8n workflow, which fans out work across agents.

## Next Suggested Files

- `docker/docker-compose.yml`
- `scripts/bootstrap_project.sh`
- `scripts/push_project.sh`
- `docs/architecture.md`
- `workflows/n8n/factory-main.json`

---

If you want, I can generate the full Docker + n8n workflow + bot starter code in the next step.
