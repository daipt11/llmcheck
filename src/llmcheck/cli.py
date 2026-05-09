import argparse
import sys
from rich.console import Console

from .config import load_models, add_model, remove_model, CONFIG_FILE
from .checker import run_check, run_list

console = Console()

def cmd_add(args):
    console.print(f"[bold cyan]Adding a new model to {CONFIG_FILE}[/bold cyan]")
    try:
        alias = input("Enter Alias (e.g., my-gpt4): ").strip()
        name = input("Enter Display Name (e.g., OpenAI GPT-4): ").strip()
        provider = input("Enter Provider (e.g., openai, anthropic, gemini): ").strip()
        model_name = input("Enter Model Name (e.g., gpt-4): ").strip()
        api_key = input("Enter API Key (press Enter to skip): ").strip()
        base_url = input("Enter Base URL (press Enter to skip): ").strip()
        
        if not alias or not name or not provider or not model_name:
            console.print("[red]Error: Alias, Name, Provider, and Model Name are required.[/red]")
            sys.exit(1)
            
        add_model(alias, name, provider, model_name, api_key, base_url)
        console.print(f"[green]Successfully added model '{alias}'.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")

def cmd_rm(args):
    alias = args.alias
    if not alias:
        console.print("[red]Error: You must provide an alias to remove.[/red]")
        sys.exit(1)
        
    if remove_model(alias):
        console.print(f"[green]Successfully removed model '{alias}'.[/green]")
    else:
        console.print(f"[red]Error: Model with alias '{alias}' not found.[/red]")

def cmd_list(args):
    models = load_models()
    run_list(models)

def cmd_check(args):
    models = load_models()
    run_check(models)

def cmd_model(args):
    models = load_models()
    target_alias = args.alias.lower()
    
    models_to_check = [m for m in models if m.get("alias", "").lower() == target_alias]
    
    if not models_to_check:
        console.print(f"[yellow]No model found with alias '{args.alias}'. Use 'llmcheck list' to see available models.[/yellow]")
        return
        
    run_check(models_to_check)

def main():
    parser = argparse.ArgumentParser(description="LLM API Health Check CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add command
    parser_add = subparsers.add_parser("add", help="Add a new model configuration")
    parser_add.set_defaults(func=cmd_add)
    
    # Rm command
    parser_rm = subparsers.add_parser("rm", help="Remove a model configuration")
    parser_rm.add_argument("alias", help="The alias of the model to remove")
    parser_rm.set_defaults(func=cmd_rm)
    
    # List command
    parser_list = subparsers.add_parser("list", help="List all configured models")
    parser_list.set_defaults(func=cmd_list)
    
    # Check command (all)
    parser_check = subparsers.add_parser("check", help="Check all configured models")
    parser_check.set_defaults(func=cmd_check)
    
    # Model command (specific)
    parser_model = subparsers.add_parser("model", help="Check a specific model by alias")
    parser_model.add_argument("alias", help="The alias of the model to check")
    parser_model.set_defaults(func=cmd_model)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
        
    # Execute the appropriate function
    args.func(args)

if __name__ == "__main__":
    main()
