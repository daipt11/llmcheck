import os
import time
import argparse
from dotenv import load_dotenv
import litellm
from rich.console import Console
from rich.table import Table

console = Console()

# Optional: suppress litellm logging if it gets noisy
litellm.suppress_debug_info = True

def load_models_from_env():
    models = {}
    for key, value in os.environ.items():
        if key.startswith("MODEL_"):
            parts = key.split("_", 2)
            if len(parts) >= 3:
                model_idx = parts[1]
                field = parts[2]
                if model_idx not in models:
                    models[model_idx] = {"_id": model_idx}
                models[model_idx][field.lower()] = value
    
    # Sort and return as list
    sorted_models = []
    for idx in sorted(models.keys(), key=lambda x: int(x) if x.isdigit() else x):
        sorted_models.append(models[idx])
    return sorted_models

def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="LLM API Health Check")
    parser.add_argument("target", nargs="?", help="Optional ID or ALIAS of the model to check (e.g. '1' or 'my-alias')")
    parser.add_argument("--id", help="Only check the model with the specific ID (e.g., 1 for MODEL_1_)")
    parser.add_argument("--name", help="Only check the model with the specific name")
    args = parser.parse_args()

    # Load .env file
    load_dotenv()
    models = load_models_from_env()
    
    if args.target:
        # Match by ID or alias (case-insensitive)
        models = [m for m in models if m.get("_id") == args.target or m.get("alias", "").lower() == args.target.lower()]
    elif args.id:
        models = [m for m in models if m.get("_id") == args.id]
    elif args.name:
        # Match name exactly but case-insensitive
        models = [m for m in models if m.get("name", "").lower() == args.name.lower()]
        
    if not models:
        console.print("[yellow]No models found matching the criteria. Please check your .env file.[/yellow]")
        return
        
    table = Table(title="LLM API Health Check Results")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Model", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Error", style="red", max_width=40)

    messages = [{"role": "user", "content": "Ping. Respond with 'pong' only."}]

    with console.status("[bold green]Pinging models...[/bold green]"):
        for config in models:
            name = config.get("name", "Unknown")
            provider = config.get("provider", "")
            model_name = config.get("model", "")
            api_key = config.get("api_key", None)
            base_url = config.get("base_url", None)
            
            # litellm routing
            # Format provider/model so litellm knows exactly which provider to use
            full_model = f"{provider}/{model_name}" if provider else model_name
            
            start_time = time.time()
            status = "❌"
            error_msg = ""
            
            try:
                # drop_params ignores parameters not supported by the provider
                litellm.drop_params = True
                
                # Make the API call
                response = litellm.completion(
                    model=full_model,
                    messages=messages,
                    api_key=api_key,
                    api_base=base_url,
                    max_tokens=10, 
                    timeout=15 # 15 seconds timeout
                )
                
                # If we get here, the call succeeded
                status = "✅"
            except Exception as e:
                # Capture the first line of the error message for the table
                error_msg = str(e).strip()
                if len(error_msg) > 100:
                    error_msg = error_msg[:97] + "..."
                
            latency = time.time() - start_time
            latency_str = f"{latency:.2f}" if status == "✅" else "-"
            
            table.add_row(name, provider, model_name, status, latency_str, error_msg)
        
    console.print(table)

if __name__ == "__main__":
    main()
