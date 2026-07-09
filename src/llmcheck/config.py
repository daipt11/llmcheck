import os
import fcntl
import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path

from dotenv import dotenv_values

# Suppress dotenv parse warnings (e.g., from litellm auto-loading unrelated .env files)
logging.getLogger('dotenv.main').setLevel(logging.ERROR)

CONFIG_FILE = Path.home() / ".llmcheck_env"
LOCK_FILE = Path.home() / ".llmcheck_env.lock"

# Required fields, written in this order. Optional fields are only written when truthy.
REQUIRED_FIELDS = [("NAME", "name"), ("PROVIDER", "provider"), ("MODEL", "model"), ("API_KEY", "api_key")]
OPTIONAL_FIELDS = [
    ("BASE_URL", "base_url"),
    ("SUPPLIER", "supplier"),
    ("TAGS", "tags"),
    ("CONTEXT", "context"),
    ("DISPLAY_ID", "display_id"),
]


def _escape(value) -> str:
    """Escape a value for safe storage inside a double-quoted dotenv line.

    Newlines/carriage-returns are collapsed to spaces (they have no legitimate
    place in a name/key/url and would corrupt the file), then backslashes and
    double-quotes are escaped so python-dotenv reads the value back verbatim.
    """
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text.replace("\\", "\\\\").replace('"', '\\"')


@contextmanager
def _locked():
    """Serialize read-modify-write cycles across concurrent CLI/web processes."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _write_lines(lines):
    """Atomically write config lines with owner-only permissions (0600)."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(CONFIG_FILE.parent), prefix=".llmcheck_env.")
    try:
        with os.fdopen(fd, "w") as f:
            f.writelines(lines)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, CONFIG_FILE)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _serialize_block(prefix, model, comment=None):
    """Build the dotenv lines (without trailing newlines) for a single model."""
    lines = []
    if comment:
        lines.append(f"# {comment}")
    for env_name, key in REQUIRED_FIELDS:
        lines.append(f'{prefix}{env_name}="{_escape(model.get(key, ""))}"')
    for env_name, key in OPTIONAL_FIELDS:
        value = model.get(key)
        if value:
            lines.append(f'{prefix}{env_name}="{_escape(value)}"')
    return lines


def load_models():
    """Loads and parses models from the config file."""
    if not CONFIG_FILE.exists():
        return []

    env_vars = dotenv_values(CONFIG_FILE)
    models = {}
    for key, value in env_vars.items():
        if key.startswith("MODEL_"):
            parts = key.split("_", 2)
            if len(parts) >= 3:
                model_idx = parts[1]
                field = parts[2]
                if model_idx not in models:
                    models[model_idx] = {"_id": model_idx}
                models[model_idx][field.lower()] = value

    sorted_models = list(models.values())

    def sort_key(m):
        val = m.get("display_id") or m.get("_id", "")
        try:
            return (0, int(val))
        except ValueError:
            return (1, str(val).lower())

    sorted_models.sort(key=sort_key)
    return sorted_models


def add_model(name, provider, model_name, api_key, base_url=None, supplier=None, tags=None, context=None, display_id=None):
    """Adds a new model configuration."""
    with _locked():
        models = load_models()

        numeric_ids = [int(m["_id"]) for m in models if m.get("_id", "").isdigit()]
        next_id = (max(numeric_ids) if numeric_ids else 0) + 1
        prefix = f"MODEL_{next_id}_"

        model = {
            "name": name,
            "provider": provider,
            "model": model_name,
            "api_key": api_key,
            "base_url": base_url,
            "supplier": supplier,
            "tags": tags,
            "context": context,
            "display_id": display_id,
        }

        existing = CONFIG_FILE.read_text().splitlines() if CONFIG_FILE.exists() else []
        block = [""] + _serialize_block(prefix, model, comment=f"Model Configuration for {name}")
        _write_lines([line + "\n" for line in existing] + [line + "\n" for line in block])


def remove_model(identifier):
    """Removes a model configuration by ID."""
    with _locked():
        if not CONFIG_FILE.exists():
            return False

        prefix = f"MODEL_{identifier}_"
        lines = CONFIG_FILE.read_text().splitlines(keepends=True)

        if not any(line.strip().startswith(prefix) for line in lines):
            return False

        kept = [line for line in lines if not line.strip().startswith(prefix)]
        _write_lines(kept)
        return True


def edit_model(identifier, updates):
    """Edits an existing model configuration by ID. updates is a dict of fields to update."""
    with _locked():
        if not CONFIG_FILE.exists():
            return False

        models = load_models()
        target_model = next((m for m in models if m.get("_id") == str(identifier)), None)
        if not target_model:
            return False

        target_model.update(updates)
        prefix = f"MODEL_{target_model['_id']}_"

        lines = CONFIG_FILE.read_text().splitlines(keepends=True)
        new_lines = []
        block_inserted = False

        for line in lines:
            if line.strip().startswith(prefix):
                if not block_inserted:
                    new_lines.extend(l + "\n" for l in _serialize_block(prefix, target_model))
                    block_inserted = True
            else:
                new_lines.append(line)

        _write_lines(new_lines)
        return True
