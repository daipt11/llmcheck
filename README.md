# llmcheck

A CLI tool to manage and health-check your LLM API configurations — supports multiple providers, parallel checking, and rich terminal output.

## Features

- ✅ **Health check** multiple LLM models with a single command
- ⚡ **Parallel execution** — models from different suppliers run concurrently
- 🔁 **Auto retry** — retries once after 5s on failure before marking as error
- 🏷️ **Multi-tag system** — label models with multiple tags (reasoning, coding, agent, etc.)
- 🔍 **Filter** by provider, supplier, or tag, and **sort** by name, supplier, or context window
- 📋 **Rich table output** with latency, status, context window, and masked API keys
- 🆔 **Custom Display IDs** — address models by your own IDs alongside internal ones
- 🛠️ Full **CRUD** for model configs (add, edit, rm, show, list)
- 🌐 **Web dashboard** for browsing and health-checking models in the browser
- 🌐 **litellm**-powered — works with OpenAI, Anthropic, Google, Azure, Groq, and 100+ providers

---

## Installation

```bash
pip install llmcheck
```

Or install from source:

```bash
git clone https://github.com/daipt11/llmcheck.git
cd llmcheck
pip install -e .
```

---

## Quick Start

```bash
# Add your first model
llmcheck add

# List all configured models
llmcheck list

# Check all models
llmcheck check

# Check specific models by ID
llmcheck model 1 2 3
```

---

## Commands

### `llmcheck add`
Interactively add a new model configuration. Prompts for:

| Field | Description |
|---|---|
| Name | Display name (e.g., `OpenAI GPT-4o`) |
| Tags | Multi-select from tag list |
| Supplier | API provider/reseller (e.g., `azure`, `groq`) |
| Context Window | Optional context size (e.g., `128k`) |
| Provider/Compatible | litellm provider prefix (e.g., `openai`, `gemini`) |
| API Key | Auto-suggested from existing models with same supplier |
| Model | Model identifier (e.g., `gpt-4o`, `claude-3-5-sonnet`) |
| Base URL | Optional custom endpoint |

---

### `llmcheck list`
Display all configured models in a table.

```bash
llmcheck list                   # all models
llmcheck list 1 2 3             # only the given IDs (internal or Display ID)
llmcheck list -p openai         # filter by provider
llmcheck list -s groq           # filter by supplier
llmcheck list -t coding         # filter by tag
llmcheck list --sort name       # sort by name (or: supplier, context)
llmcheck list -v                # verbose: show full model information
```

---

### `llmcheck show <id>`
Show full details of a model, including the **unmasked API key**.

```bash
llmcheck show 1
```

```
╭─── Model #1 ───────────────────────────────────────────╮
│              ID  1                                      │
│            Name  OpenAI GPT-4o                          │
│            Tags  coding,general                         │
│        Supplier  -                                      │
│ Provider/Compatible  openai                             │
│         API Key  sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx       │
│           Model  gpt-4o                                 │
│         Context  128k                                   │
│        Base URL  -                                      │
╰─────────────────────────────────────────────────────────╯
```

---

### `llmcheck check`
Health-check **all** configured models.

```bash
llmcheck check           # check all
llmcheck check -v        # verbose: show full error messages
```

Models with the same supplier are checked **sequentially**; models across different suppliers run **in parallel**.

Each failed model is **retried once after 5 seconds** before being marked as ❌.

---

### `llmcheck model <id> [id ...]`
Check one or more specific models by ID.

```bash
llmcheck model 1
llmcheck model 1 3 5
llmcheck model 2 -v
```

---

### `llmcheck edit <id>`
Interactively edit an existing model. Press Enter to keep the current value.

```bash
llmcheck edit 1
```

---

### `llmcheck rm <id>`
Remove a model from the config.

```bash
llmcheck rm 3
```

`show`, `edit`, `rm`, and `model` accept either the internal ID or a custom Display ID.

---

### `llmcheck web`
Start the local web dashboard.

```bash
llmcheck web                 # http://127.0.0.1:6565
llmcheck web -p 8080         # custom port
llmcheck web --host 0.0.0.0  # expose on your network (see warning below)
```

> ⚠️ **Security:** the dashboard API returns **unmasked API keys** to any client
> that can reach it. It binds to `127.0.0.1` by default. Only pass `--host 0.0.0.0`
> on a trusted network, ideally behind an authenticating reverse proxy.

For a persistent, auto-restarting service, use the provided systemd user unit:
[`deploy/llmcheck-web.service`](deploy/llmcheck-web.service).

---

## Tags

When adding or editing a model, you can select multiple tags from the following list:

| Tag | Description |
|---|---|
| `reasoning` | Suy luận mạnh |
| `general` | Đa năng |
| `coding` | Lập trình / Code |
| `agent` | Agent, Tool-use, Search |
| `fast` | Tốc độ cao |
| `lite` | Nhẹ, tiết kiệm |
| `vision` | Xử lý hình ảnh |
| `large` | Model lớn, mạnh |

You can also add **custom tags** by entering `+` in the tag selection menu.

---

## Config File

All model configurations are stored in `~/.llmcheck_env` as a dotenv-style file:

```env
# Model Configuration for GPT-4o
MODEL_1_NAME="GPT-4o"
MODEL_1_PROVIDER="openai"
MODEL_1_MODEL="gpt-4o"
MODEL_1_API_KEY="sk-..."
MODEL_1_TAGS="general,coding"
MODEL_1_SUPPLIER="azure"
MODEL_1_CONTEXT="128k"
MODEL_1_BASE_URL=""
MODEL_1_DISPLAY_ID=""
```

---

## Dependencies

- [litellm](https://github.com/BerriAI/litellm) — unified LLM API client
- [rich](https://github.com/Textualize/rich) — terminal formatting
- [python-dotenv](https://github.com/theskumar/python-dotenv) — config parsing
- [fastapi](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) — web dashboard

The config file `~/.llmcheck_env` holds your API keys and is written with
owner-only permissions (`0600`). Writes are atomic and file-locked, so the CLI
and web UI can safely run at the same time.

---

## Development

```bash
pip install -e ".[dev]"
pytest        # run the test suite
ruff check .  # lint
```

---

## License

MIT
