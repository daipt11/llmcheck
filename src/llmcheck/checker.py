import time
import litellm
from rich.console import Console
from rich.table import Table

console = Console()
litellm.suppress_debug_info = True

def run_check(models_to_check):
    if not models_to_check:
        console.print("[yellow]No models found to check.[/yellow]")
        return

    table = Table(title="LLM API Health Check Results")
    table.add_column("Alias", style="yellow")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Model", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Error", style="red", max_width=40)

    messages = [{"role": "user", "content": "Ping. Respond with 'pong' only."}]

    with console.status("[bold green]Pinging models...[/bold green]"):
        for config in models_to_check:
            alias = config.get("alias", "")
            name = config.get("name", "Unknown")
            provider = config.get("provider", "")
            model_name = config.get("model", "")
            api_key = config.get("api_key", None)
            base_url = config.get("base_url", None)
            
            full_model = f"{provider}/{model_name}" if provider else model_name
            
            start_time = time.time()
            status = "❌"
            error_msg = ""
            
            try:
                litellm.drop_params = True
                response = litellm.completion(
                    model=full_model,
                    messages=messages,
                    api_key=api_key,
                    api_base=base_url,
                    max_tokens=10, 
                    timeout=15
                )
                status = "✅"
            except Exception as e:
                error_msg = str(e).strip()
                if len(error_msg) > 100:
                    error_msg = error_msg[:97] + "..."
                
            latency = time.time() - start_time
            latency_str = f"{latency:.2f}" if status == "✅" else "-"
            
            table.add_row(alias, name, provider, model_name, status, latency_str, error_msg)
        
    console.print(table)

def run_list(models):
    if not models:
        console.print("[yellow]No models configured. Use 'llmcheck add' to add one.[/yellow]")
        return
        
    table = Table(title="Configured Models")
    table.add_column("Alias", style="yellow")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Model", style="blue")
    table.add_column("Base URL", style="green")
    
    for m in models:
        table.add_row(
            m.get("alias", ""),
            m.get("name", ""),
            m.get("provider", ""),
            m.get("model", ""),
            m.get("base_url", "-")
        )
        
    console.print(table)
