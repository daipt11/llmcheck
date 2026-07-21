import queue
import time
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.live import Live
from rich.table import Table

from .util import mask_key

console = Console()

# Cap total concurrent supplier groups so a large config can't spawn unbounded threads.
MAX_WORKERS = 16
RETRY_DELAY = 5

# HTTP statuses worth retrying. Auth/not-found/bad-request (401/403/404/400) are
# permanent — retrying just doubles the wait for a guaranteed failure.
TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

PING_MESSAGES = [{"role": "user", "content": "Ping. Respond with 'pong' only."}]


def _is_transient(exc) -> bool:
    """Return True for errors likely to succeed on retry (timeouts, rate limits, 5xx)."""
    status = getattr(exc, "status_code", None)
    if status is None:
        # Network errors / timeouts carry no status code — treat as transient.
        return True
    try:
        return int(status) in TRANSIENT_STATUS
    except (TypeError, ValueError):
        return True


def _result(config, status, latency, error_msg):
    latency_str = f"{latency:.2f}" if status == "✅" else "-"
    return {
        "id": config.get("_id", ""),
        "display_id": config.get("display_id", ""),
        "name": config.get("name", "Unknown"),
        "tags": config.get("tags", ""),
        "context": config.get("context", "-"),
        "supplier": config.get("supplier", ""),
        "provider": config.get("provider", ""),
        "api_key": mask_key(config.get("api_key", "")),
        "model": config.get("model", ""),
        "status": status,
        "latency": latency_str,
        "error": error_msg,
    }


def check_single_model(config, messages, verbose=False):
    # Lazy import: litellm is heavy (~seconds) and only needed for actual checks,
    # so non-checking commands (list/show/add/edit) stay fast.
    import litellm
    litellm.suppress_debug_info = True
    litellm.drop_params = True

    provider = config.get("provider", "")
    model_name = config.get("model", "")
    full_model = f"{provider}/{model_name}" if provider else model_name

    for attempt in range(2):
        start_time = time.time()
        try:
            litellm.completion(
                model=full_model,
                messages=messages,
                api_key=config.get("api_key", None),
                api_base=config.get("base_url", None),
                max_tokens=10,
                timeout=15,
            )
            return _result(config, "✅", time.time() - start_time, "")
        except Exception as e:
            error_msg = str(e).strip()
            if attempt == 0 and _is_transient(e):
                time.sleep(RETRY_DELAY)
                continue
            if not verbose and len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            return _result(config, "❌", 0, error_msg)


def check_group(group_models, messages, verbose, result_queue):
    for m in group_models:
        result_queue.put(check_single_model(m, messages, verbose))


def _row(r):
    return (
        r.get("display_id") or r["id"], r["name"], r["tags"], r["context"], r["supplier"],
        r["provider"], r["api_key"], r["model"], r["status"], r["latency"], r["error"],
    )


def _row_compact(r):
    return (
        r.get("display_id") or r["id"], r["name"], r["supplier"],
        r["status"], r["latency"], r["error"],
    )


def _group_by_supplier(models):
    groups = {}
    for m in models:
        key = str(m.get("supplier") or m.get("provider") or m.get("_id")).strip().lower()
        groups.setdefault(key, []).append(m)
    return groups


def run_check(models_to_check, verbose=False, compact=False):
    if not models_to_check:
        console.print("[yellow]No models found to check.[/yellow]")
        return

    table = Table(title="LLM API Health Check Results")
    table.add_column("ID", style="bold green", justify="right")
    table.add_column("Name", style="cyan")
    if not compact:
        table.add_column("Tags", style="yellow")
        table.add_column("Context", style="magenta")
    table.add_column("Supplier", style="cyan")
    if not compact:
        table.add_column("Provider/Compatible", style="magenta")
        table.add_column("API Key", style="dim")
        table.add_column("Model", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Error", style="red", max_width=None if verbose else 40)

    build_row = _row_compact if compact else _row
    groups = _group_by_supplier(models_to_check)
    result_queue = queue.Queue()

    console.print("[bold green]Pinging models...[/bold green]")
    with Live(table, console=console, refresh_per_second=4):
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(groups))) as executor:
            for group_models in groups.values():
                executor.submit(check_group, group_models, PING_MESSAGES, verbose, result_queue)

            for _ in range(len(models_to_check)):
                table.add_row(*build_row(result_queue.get()))


def run_list(models, verbose=False):
    if not models:
        console.print("[yellow]No models configured. Use 'llmcheck add' to add one.[/yellow]")
        return

    table = Table(title="Configured Models")
    table.add_column("ID", style="bold green", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Tags", style="yellow")
    table.add_column("Context", style="magenta")
    table.add_column("Supplier", style="cyan")

    if verbose:
        table.add_column("Provider/Compatible", style="magenta")
        table.add_column("API Key", style="dim")
        table.add_column("Model", style="blue")
        table.add_column("Base URL", style="green")

    for m in models:
        row_data = [
            m.get("display_id") or m.get("_id", ""),
            m.get("name", ""),
            m.get("tags", ""),
            m.get("context", "-"),
            m.get("supplier", ""),
        ]
        if verbose:
            row_data.extend([
                m.get("provider", ""),
                mask_key(m.get("api_key", "")),
                m.get("model", ""),
                m.get("base_url", "-"),
            ])
        table.add_row(*row_data)

    console.print(table)
