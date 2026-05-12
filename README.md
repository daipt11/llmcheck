# llmcheck

A CLI tool to manage and health-check your LLM API configurations — supports multiple providers, parallel checking, and rich terminal output.

## Features

- ✅ **Health check** multiple LLM models with a single command
- ⚡ **Parallel execution** — models from different suppliers run concurrently
- 🔁 **Auto retry** — retries once after 5s on failure before marking as error
- 🏷️ **Multi-tag system** — label models with multiple tags (reasoning, coding, agent, etc.)
- 🔍 **Filter** by provider, supplier, or tag
- 📋 **Rich table output** with latency, status, and masked API keys
- 🛠️ Full **CRUD** for model configs (add, edit, rm, show, list)
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
| Provider/Compatible | litellm provider prefix (e.g., `openai`, `gemini`) |
| API Key | Auto-suggested from existing models with same supplier |
| Model | Model identifier (e.g., `gpt-4o`, `claude-3-5-sonnet`) |
| Base URL | Optional custom endpoint |

---

### `llmcheck list`
Display all configured models in a table.

```bash
llmcheck list                   # all models
llmcheck list -p openai         # filter by provider
llmcheck list -s groq           # filter by supplier
llmcheck list -t coding         # filter by tag
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
```

---

## Dependencies

- [litellm](https://github.com/BerriAI/litellm) — unified LLM API client
- [rich](https://github.com/Textualize/rich) — terminal formatting
- [python-dotenv](https://github.com/theskumar/python-dotenv) — config parsing

---

## License

MIT
