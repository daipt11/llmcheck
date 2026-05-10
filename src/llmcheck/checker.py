import time
import litellm
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.live import Live
import queue

console = Console()
litellm.suppress_debug_info = True
litellm.drop_params = True

def check_single_model(config, messages, verbose=False):
    name = config.get("name", "Unknown")
    provider = config.get("provider", "")
    model_name = config.get("model", "")
    supplier = config.get("supplier", "")
    tags = config.get("tags", "")
    api_key = config.get("api_key", None)
    base_url = config.get("base_url", None)
    
    full_model = f"{provider}/{model_name}" if provider else model_name
    
    status = "❌"
    error_msg = ""
    latency = 0
    
    for attempt in range(2):
        start_time = time.time()
        try:
            response = litellm.completion(
                model=full_model,
                messages=messages,
                api_key=api_key,
                api_base=base_url,
                max_tokens=10, 
                timeout=15
            )
            status = "✅"
            latency = time.time() - start_time
            break
        except Exception as e:
            error_msg = str(e).strip()
            latency = time.time() - start_time
            if attempt == 0:
                time.sleep(5)
                
    if status == "❌":
        if not verbose and len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."
    else:
        error_msg = ""
        
    # Shorten API Key for display
    display_key = "-"
    if api_key:
        if len(api_key) > 8:
            display_key = f"{api_key[:4]}...{api_key[-4:]}"
        else:
            display_key = "***"

    latency_str = f"{latency:.2f}" if status == "✅" else "-"
    
    return (config.get("_id", ""), name, tags, supplier, provider, display_key, model_name, status, latency_str, error_msg)

def check_group(group_models, messages, verbose, result_queue):
    for m in group_models:
        try:
            result = check_single_model(m, messages, verbose)
        except Exception as e:
            # Handle API key masking in error case too
            api_key = m.get("api_key", "")
            display_key = "-"
            if api_key:
                if len(api_key) > 8:
                    display_key = f"{api_key[:4]}...{api_key[-4:]}"
                else:
                    display_key = "***"
            result = (m.get("_id", ""), m.get("name", "Unknown"), m.get("tags", ""), m.get("supplier", ""), m.get("provider", ""), display_key, m.get("model", ""), "❌", "-", str(e))
        result_queue.put(result)

def run_check(models_to_check, verbose=False):
    if not models_to_check:
        console.print("[yellow]No models found to check.[/yellow]")
        return

    table = Table(title="LLM API Health Check Results")
    table.add_column("ID", style="bold green", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Tags", style="yellow")
    table.add_column("Supplier", style="cyan")
    table.add_column("Provider/Compatible", style="magenta")
    table.add_column("API Key", style="dim")
    table.add_column("Model", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Error", style="red", max_width=None if verbose else 40)

    messages = [{"role": "user", "content": "Ping. Respond with 'pong' only."}]

    groups = {}
    for m in models_to_check:
        key = str(m.get("supplier") or m.get("provider") or m.get("_id")).strip().lower()
        groups.setdefault(key, []).append(m)

    result_queue = queue.Queue()

    console.print("[bold green]Pinging models...[/bold green]")
    with Live(table, console=console, refresh_per_second=4):
        with ThreadPoolExecutor(max_workers=max(1, len(groups))) as executor:
            for key, group_models in groups.items():
                executor.submit(check_group, group_models, messages, verbose, result_queue)
                
            for _ in range(len(models_to_check)):
                row_data = result_queue.get()
                table.add_row(*row_data)

def run_list(models):
    if not models:
        console.print("[yellow]No models configured. Use 'llmcheck add' to add one.[/yellow]")
        return
        
    table = Table(title="Configured Models")
    table.add_column("ID", style="bold green", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Tags", style="yellow")
    table.add_column("Supplier", style="cyan")
    table.add_column("Provider/Compatible", style="magenta")
    table.add_column("API Key", style="dim")
    table.add_column("Model", style="blue")
    table.add_column("Base URL", style="green")
    
    for m in models:
        api_key = m.get("api_key", "")
        display_key = "-"
        if api_key:
            if len(api_key) > 8:
                display_key = f"{api_key[:4]}...{api_key[-4:]}"
            else:
                display_key = "***"

        table.add_row(
            m.get("_id", ""),
            m.get("name", ""),
            m.get("tags", ""),
            m.get("supplier", ""),
            m.get("provider", ""),
            display_key,
            m.get("model", ""),
            m.get("base_url", "-")
        )
        
    console.print(table)

