import time
import litellm
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.live import Live

console = Console()
litellm.suppress_debug_info = True
litellm.drop_params = True

def check_single_model(config, messages, verbose=False):
    alias = config.get("alias", "")
    name = config.get("name", "Unknown")
    provider = config.get("provider", "")
    model_name = config.get("model", "")
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
        
    latency_str = f"{latency:.2f}" if status == "✅" else "-"
    
    return (config.get("_id", ""), alias, name, provider, model_name, status, latency_str, error_msg)

def check_provider_models(models, messages, verbose, table):
    for m in models:
        row_data = check_single_model(m, messages, verbose)
        table.add_row(*row_data)

def run_check(models_to_check, verbose=False):
    if not models_to_check:
        console.print("[yellow]No models found to check.[/yellow]")
        return

    table = Table(title="LLM API Health Check Results")
    table.add_column("ID", style="bold green", justify="right")
    table.add_column("Alias", style="yellow")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Model", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Error", style="red", max_width=None if verbose else 40)

    messages = [{"role": "user", "content": "Ping. Respond with 'pong' only."}]

    provider_groups = {}
    for m in models_to_check:
        provider = m.get("provider", "unknown").lower()
        if provider not in provider_groups:
            provider_groups[provider] = []
        provider_groups[provider].append(m)

    console.print("[bold green]Pinging models...[/bold green]")
    with Live(table, console=console, refresh_per_second=4):
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_provider_models, group, messages, verbose, table) for group in provider_groups.values()]
            for future in as_completed(futures):
                future.result()

def run_list(models):
    if not models:
        console.print("[yellow]No models configured. Use 'llmcheck add' to add one.[/yellow]")
        return
        
    table = Table(title="Configured Models")
    table.add_column("ID", style="bold green", justify="right")
    table.add_column("Alias", style="yellow")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Model", style="blue")
    table.add_column("Base URL", style="green")
    
    for m in models:
        table.add_row(
            m.get("_id", ""),
            m.get("alias", ""),
            m.get("name", ""),
            m.get("provider", ""),
            m.get("model", ""),
            m.get("base_url", "-")
        )
        
    console.print(table)
