# SpecAgent

SpecAgent is an autonomous, spec-driven development agent. It takes a feature request through specification, architecture, code generation, test generation, review, and delivery. A live dashboard displays pipeline progress and supports human-in-the-loop (HITM) approvals.

## Requirements

- Python 3.11 or newer
- An API key for one supported LLM provider: GitHub Models, Azure OpenAI, or OpenAI

## Setup

Create and activate a virtual environment, then install the dependencies.

### Windows (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and configure **one** provider. GitHub Models is the default when neither Azure OpenAI nor OpenAI credentials are set:

```dotenv
GITHUB_TOKEN=your_github_token
GITHUB_MODEL=gpt-4o
```

The GitHub token must have permission to access GitHub Models. Alternatively, configure Azure OpenAI with `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`, or OpenAI with `OPENAI_API_KEY`. If credentials for multiple providers are set, provider detection prioritizes Azure OpenAI, then OpenAI, then GitHub Models.

Other settings in `.env.example` control HITM, model generation, dashboard binding, and output directories. Do not commit `.env` or expose API keys.

## Usage

Run commands from the repository root with the virtual environment activated.

### Start a pipeline

```bash
python main.py run "Build a REST API for a product catalogue" --title "Product Catalogue API"
```

The dashboard starts alongside the pipeline by default at `http://localhost:8000`. To use another port or host:

```bash
python main.py run "Build a todo API" --host 127.0.0.1 --port 8080
```

To provide a longer request from a file:

```bash
python main.py run --file feature.txt --title "My Feature"
```

HITM is enabled by default through `HITM_MODE` in `.env` (default: `true`). Use `--no-hitm` to run without approval checkpoints, or `--hitm` to enable them for a single run. HITM checkpoints pause the pipeline for approval after the specification, architecture, and code review stages.

To run without the dashboard:

```bash
python main.py run "Build a todo API" --no-dashboard
```

### Run the dashboard only

```bash
python main.py dashboard
```

Then open `http://localhost:8000`. Choose a host or port with `--host` and `--port`.

### Show resolved configuration

```bash
python main.py config
```

The installed CLI entry point is also available after installation with `pip install -e .`:

```bash
specagent --help
specagent run "Build a todo API"
specagent dashboard
specagent config
```

## Dashboard API

The FastAPI dashboard exposes:

- `GET /api/state` — current pipeline state
- `POST /api/run` — start a pipeline with a JSON body containing `title`, `description`, and optional `hitm`
- `POST /api/hitm/resolve` — approve or reject a HITM checkpoint
- `GET /api/output/{task_id}` — list files generated for a task
- `WS /ws` — real-time state and event stream

The interactive dashboard is served at `/`.

## Pipeline and generated files

The coordinator runs these stages:

1. Intake and specification
2. Architecture
3. Code generation
4. Test generation
5. Code review
6. Delivery

Generated deliverables are saved under `output/<task_id>/`. Specifications are stored under `specs/`. Both locations can be changed with `OUTPUT_DIR` and `SPECS_DIR` in `.env`.

## Project layout

- `agents/` — specialist specification, architecture, coding, testing, and review agents
- `config/` — environment-backed application settings
- `core/` — shared state management and event bus
- `dashboard/` — FastAPI server and browser dashboard
- `models/` — task, agent-state, and specification models
- `orchestrator/` — pipeline coordination
- `speckit/` — specification generation support
- `main.py` — Typer command-line entry point
