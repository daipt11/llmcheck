import argparse
import sys
from rich.console import Console
from rich.prompt import Prompt

from .config import load_models, add_model, remove_model, edit_model, CONFIG_FILE
from .checker import run_check, run_list

console = Console()

def prompt_category(default_val=None):
    categories = [
        ("Reasoning", "Strong Reasoning", "Suy luận, logic, toán học, task phức tạp"),
        ("General", "General Purpose", "Đa năng, chat, công việc thông thường"),
        ("Coding", "Coding & Programming", "Viết code, debug, lập trình"),
        ("Agent", "Agent & Tool Use", "Agent, tool calling, search, workflow"),
        ("Fast", "Fast & Lite", "Tốc độ cao, chi phí thấp, volume lớn"),
        ("Vision", "Vision & Multimodal", "Xử lý hình ảnh, vision"),
        ("Custom", "Thêm mới...", "")
    ]
    
    console.print("\n[bold cyan]Select Category:[/bold cyan]")
    for i, (cat, name, desc) in enumerate(categories, 1):
        if desc:
            console.print(f"  [green]{i}.[/green] [bold]{cat}[/bold] ({name}) - {desc}")
        else:
            console.print(f"  [green]{i}.[/green] [bold]{cat}[/bold] - {name}")
            
    choices = [str(i) for i in range(1, len(categories) + 1)]
    default_idx = None
    
    if default_val:
        for i, (cat, _, _) in enumerate(categories[:-1], 1):
            if cat.lower() == default_val.lower():
                default_idx = str(i)
                break
        if not default_idx:
            default_idx = str(len(categories)) # Custom
            
    prompt_kwargs = {"choices": choices, "show_choices": False}
    if default_idx:
        prompt_kwargs["default"] = default_idx
        
    choice = Prompt.ask("Enter your choice", **prompt_kwargs)
    idx = int(choice) - 1
    
    if idx == len(categories) - 1: # Custom
        prompt_str = f"Enter Custom Category"
        if default_val:
            prompt_str += f" [{default_val}]"
        prompt_str += ": "
        custom_val = input(prompt_str).strip()
        return custom_val if custom_val else (default_val if default_val else "")
    else:
        return categories[idx][0].lower()

def cmd_add(args):
    console.print(f"[bold cyan]Adding a new model to {CONFIG_FILE}[/bold cyan]")
    try:
        name = input("Enter Display Name (e.g., OpenAI GPT-4): ").strip()
        category = prompt_category()
        supplier = input("Enter Supplier (e.g., azure, groq) [optional]: ").strip()
        provider = input("Enter Provider (e.g., openai, anthropic, gemini): ").strip()
        model_name = input("Enter Model Name (e.g., gpt-4): ").strip()
        
        models = load_models()
        existing_models = [m for m in models if m.get("supplier", "").lower() == supplier.lower()] if supplier else []
        if not existing_models:
            existing_models = [m for m in models if m.get("provider", "").lower() == provider.lower()]
        
        suggested_key = ""
        suggested_base_url = ""
        for m in existing_models:
            if not suggested_key and m.get("api_key"):
                suggested_key = m.get("api_key")
            if not suggested_base_url and m.get("base_url"):
                suggested_base_url = m.get("base_url")
                    
        if suggested_key:
            display_key = f"{suggested_key[:4]}...{suggested_key[-4:]}" if len(suggested_key) > 8 else "***"
            api_key = input(f"Enter API Key [{display_key}]: ").strip()
            if not api_key:
                api_key = suggested_key
        else:
            api_key = input("Enter API Key (press Enter to skip): ").strip()
            
        if suggested_base_url:
            base_url = input(f"Enter Base URL [{suggested_base_url}]: ").strip()
            if not base_url:
                base_url = suggested_base_url
        else:
            base_url = input("Enter Base URL (press Enter to skip): ").strip()
        
        if not name or not provider or not model_name:
            console.print("[red]Error: Name, Provider, and Model Name are required.[/red]")
            sys.exit(1)
            
        add_model(name, provider, model_name, api_key, base_url, supplier, category)
        console.print(f"[green]Successfully added model '{name}'.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")

def cmd_rm(args):
    identifier = args.identifier
    if not identifier:
        console.print("[red]Error: You must provide an ID to remove.[/red]")
        sys.exit(1)
        
    if remove_model(identifier):
        console.print(f"[green]Successfully removed model '{identifier}'.[/green]")
    else:
        console.print(f"[red]Error: Model with ID '{identifier}' not found.[/red]")

def cmd_edit(args):
    identifier = args.identifier
    models = load_models()
    target_model = None
    for m in models:
        if m.get("_id") == str(identifier):
            target_model = m
            break
            
    if not target_model:
        console.print(f"[red]Error: Model with ID '{identifier}' not found.[/red]")
        sys.exit(1)
        
    console.print(f"[bold cyan]Editing model '{identifier}' in {CONFIG_FILE}[/bold cyan]")
    console.print("[dim]Press Enter to keep the current value.[/dim]")
    
    try:
        name = input(f"Enter Display Name [{target_model.get('name', '')}]: ").strip()
        
        current_category = target_model.get('category', '')
        new_category = prompt_category(current_category)
        category = new_category if new_category != current_category else ""
        
        supplier = input(f"Enter Supplier [{target_model.get('supplier', '')}]: ").strip()
        provider = input(f"Enter Provider [{target_model.get('provider', '')}]: ").strip()
        model_name = input(f"Enter Model Name [{target_model.get('model', '')}]: ").strip()
        
        # Mask API key for display
        current_key = target_model.get('api_key', '')
        display_key = f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else "***" if current_key else "None"
        api_key = input(f"Enter API Key [{display_key}]: ").strip()
        
        current_base_url = target_model.get('base_url', '')
        base_url = input(f"Enter Base URL (type 'none' to clear) [{current_base_url}]: ").strip()
        
        updates = {}
        if name: updates['name'] = name
        if provider: updates['provider'] = provider
        if model_name: updates['model'] = model_name
        if supplier: updates['supplier'] = supplier
        if category: updates['category'] = category
        if api_key: updates['api_key'] = api_key
        if base_url:
            if base_url.lower() == 'none':
                updates['base_url'] = ""
            else:
                updates['base_url'] = base_url
                
        if not updates:
            console.print("[yellow]No changes made.[/yellow]")
            return
            
        if edit_model(identifier, updates):
            console.print(f"[green]Successfully updated model '{identifier}'.[/green]")
        else:
            console.print(f"[red]Failed to update model '{identifier}'.[/red]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")

def cmd_list(args):
    models = load_models()
    
    if args.provider:
        models = [m for m in models if m.get("provider", "").lower() == args.provider.lower()]
    if args.supplier:
        models = [m for m in models if m.get("supplier", "").lower() == args.supplier.lower()]
    if args.category:
        models = [m for m in models if m.get("category", "").lower() == args.category.lower()]
        
    if not models:
        console.print("[yellow]No models found matching the criteria.[/yellow]")
        return
            
    run_list(models)

def cmd_check(args):
    models = load_models()
    run_check(models, verbose=args.verbose)

def cmd_model(args):
    models = load_models()
    targets = [str(t).lower() for t in args.identifiers]
    
    models_to_check = [m for m in models if m.get("_id") in targets]
    
    if not models_to_check:
        console.print(f"[yellow]No models found with IDs: {', '.join(args.identifiers)}. Use 'llmcheck list' to see available models.[/yellow]")
        return
        
    run_check(models_to_check, verbose=args.verbose)

def main():
    parser = argparse.ArgumentParser(description="LLM API Health Check CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add command
    parser_add = subparsers.add_parser("add", help="Add a new model configuration")
    parser_add.set_defaults(func=cmd_add)
    
    # Rm command
    parser_rm = subparsers.add_parser("rm", help="Remove a model configuration")
    parser_rm.add_argument("identifier", help="The ID of the model to remove")
    parser_rm.set_defaults(func=cmd_rm)
    
    # Edit command
    parser_edit = subparsers.add_parser("edit", help="Edit an existing model configuration")
    parser_edit.add_argument("identifier", help="The ID of the model to edit")
    parser_edit.set_defaults(func=cmd_edit)
    
    # List command
    parser_list = subparsers.add_parser("list", help="List all configured models")
    parser_list.add_argument("-p", "--provider", help="Optional provider name to filter by (e.g., openai)")
    parser_list.add_argument("-s", "--supplier", help="Optional supplier name to filter by")
    parser_list.add_argument("-c", "--category", help="Optional category name to filter by")
    parser_list.set_defaults(func=cmd_list)
    
    # Check command (all)
    parser_check = subparsers.add_parser("check", help="Check all configured models")
    parser_check.add_argument("-v", "--verbose", action="store_true", help="Show detailed error messages without truncation")
    parser_check.set_defaults(func=cmd_check)
    
    # Model command (specific)
    parser_model = subparsers.add_parser("model", help="Check specific models by ID")
    parser_model.add_argument("identifiers", nargs="+", help="The IDs of the models to check")
    parser_model.add_argument("-v", "--verbose", action="store_true", help="Show detailed error messages without truncation")
    parser_model.set_defaults(func=cmd_model)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
        
    # Execute the appropriate function
    args.func(args)

if __name__ == "__main__":
    main()
