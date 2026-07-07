import argparse
import sys
from rich.console import Console
from rich.prompt import Prompt

from .config import load_models, add_model, remove_model, edit_model, CONFIG_FILE
from .checker import run_check, run_list

console = Console()

AVAILABLE_TAGS = [
    ("reasoning", "Reasoning",  "Suy luận mạnh"),
    ("general",   "General",    "Đa năng"),
    ("coding",    "Coding",     "Lập trình / Code"),
    ("agent",     "Agent",      "Agent, Tool-use, Search"),
    ("fast",      "Fast",       "Tốc độ cao"),
    ("lite",      "Lite",       "Nhẹ, tiết kiệm"),
    ("vision",    "Vision",     "Xử lý hình ảnh"),
    ("large",     "Large",      "Model lớn, mạnh"),
]

def prompt_tags(current_tags=None):
    """Display a multi-select menu for tags. Returns comma-separated tag string."""
    selected = set()
    if current_tags:
        for t in current_tags.split(","):
            t = t.strip().lower()
            if t:
                selected.add(t)

    while True:
        console.print("\n[bold cyan]Select Tags[/bold cyan] [dim](currently selected shown with ✓)[/dim]")
        for i, (tag, name, desc) in enumerate(AVAILABLE_TAGS, 1):
            tick = "[green]✓[/green] " if tag in selected else "  "
            console.print(f"  {tick}[green]{i}.[/green] [bold]{tag}[/bold] ({name}) - {desc}")
        console.print(f"  [yellow]+.[/yellow] [bold]Thêm tag mới...[/bold]")
        console.print(f"  [green]0.[/green] [bold]Done[/bold] - Confirm selection")

        choices = [str(i) for i in range(0, len(AVAILABLE_TAGS) + 1)] + ["+"]
        choice = Prompt.ask("Toggle tag (number), + to add custom, 0 to confirm", choices=choices, show_choices=False)

        if choice == "0":
            break
        elif choice == "+":
            custom_tag = input("Enter custom tag name: ").strip().lower()
            if custom_tag:
                selected.add(custom_tag)
        else:
            idx = int(choice)
            tag = AVAILABLE_TAGS[idx - 1][0]
            if tag in selected:
                selected.discard(tag)
            else:
                selected.add(tag)

    return ",".join(sorted(selected))

def cmd_add(args):
    console.print(f"[bold cyan]Adding a new model to {CONFIG_FILE}[/bold cyan]")
    try:
        name = input("Enter Display Name (e.g., OpenAI GPT-4): ").strip()
        tags = prompt_tags()
        supplier = input("Enter Supplier (e.g., azure, groq) [optional]: ").strip()
        context = input("Enter Context Window (e.g., 128k) [optional]: ").strip()
        provider = input("Enter Provider/Compatible (e.g., openai, anthropic, gemini): ").strip()

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

        model_name = input("Enter Model Name (e.g., gpt-4): ").strip()

        if suggested_base_url:
            base_url = input(f"Enter Base URL [{suggested_base_url}]: ").strip()
            if not base_url:
                base_url = suggested_base_url
        else:
            base_url = input("Enter Base URL (press Enter to skip): ").strip()

        if not name or not provider or not model_name:
            console.print("[red]Error: Name, Provider, and Model Name are required.[/red]")
            sys.exit(1)

        add_model(name, provider, model_name, api_key, base_url, supplier, tags, context)
        console.print(f"[green]Successfully added model '{name}'.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")

def cmd_show(args):
    identifier = str(args.identifier)
    models = load_models()
    target = next((m for m in models if m.get("_id") == identifier), None)

    if not target:
        console.print(f"[red]Error: Model with ID '{identifier}' not found.[/red]")
        sys.exit(1)

    from rich.panel import Panel
    from rich.table import Table

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column(style="bold cyan", justify="right")
    t.add_column(style="white")

    fields = [
        ("ID",                  target.get("display_id") or target.get("_id", "")),
        ("Name",                target.get("name", "")),
        ("Tags",                target.get("tags", "-")),
        ("Supplier",            target.get("supplier", "-")),
        ("Provider/Compatible", target.get("provider", "")),
        ("API Key",             target.get("api_key", "") or "-"),
        ("Model",               target.get("model", "")),
        ("Context",             target.get("context", "-")),
        ("Base URL",            target.get("base_url", "-")),
    ]
    for label, value in fields:
        t.add_row(label, value or "-")

    console.print(Panel(t, title=f"[bold green]Model #{identifier}[/bold green]", expand=False))

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

        current_tags = target_model.get('tags', '')
        new_tags = prompt_tags(current_tags)
        tags = new_tags  # always update (even if unchanged, harmless)

        supplier = input(f"Enter Supplier [{target_model.get('supplier', '')}]: ").strip()
        context = input(f"Enter Context Window [{target_model.get('context', '')}]: ").strip()
        provider = input(f"Enter Provider/Compatible [{target_model.get('provider', '')}]: ").strip()

        # Mask API key for display
        current_key = target_model.get('api_key', '')
        display_key = f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else "***" if current_key else "None"
        api_key = input(f"Enter API Key [{display_key}]: ").strip()

        model_name = input(f"Enter Model Name [{target_model.get('model', '')}]: ").strip()

        current_base_url = target_model.get('base_url', '')
        base_url = input(f"Enter Base URL (type 'none' to clear) [{current_base_url}]: ").strip()

        updates = {}
        if name: updates['name'] = name
        if provider: updates['provider'] = provider
        if model_name: updates['model'] = model_name
        if supplier: updates['supplier'] = supplier
        updates['context'] = context  # always write context (can be empty string to clear)
        updates['tags'] = tags  # always write tags (can be empty string to clear)
        if api_key: updates['api_key'] = api_key
        if base_url:
            if base_url.lower() == 'none':
                updates['base_url'] = ""
            else:
                updates['base_url'] = base_url

        if edit_model(identifier, updates):
            console.print(f"[green]Successfully updated model '{identifier}'.[/green]")
        else:
            console.print(f"[red]Failed to update model '{identifier}'.[/red]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")

def cmd_web(args):
    try:
        import uvicorn
    except ImportError:
        console.print("[red]Error: uvicorn is not installed. Run: pip install uvicorn[/red]")
        sys.exit(1)

    port = args.port
    console.print(f"[bold green]Starting llmcheck Web UI at http://localhost:{port}[/bold green]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    uvicorn.run("llmcheck.web:app", host="0.0.0.0", port=port, reload=False)


def cmd_list(args):
    models = load_models()

    if getattr(args, "ids", None):
        models = [m for m in models if m.get("_id") in args.ids]

    if args.provider:
        models = [m for m in models if m.get("provider", "").lower() == args.provider.lower()]
    if args.supplier:
        models = [m for m in models if m.get("supplier", "").lower() == args.supplier.lower()]
    if args.tag:
        models = [m for m in models if args.tag.lower() in [t.strip() for t in m.get("tags", "").lower().split(",")]]

    if args.sort:
        if args.sort == "name":
            models.sort(key=lambda m: m.get("name", "").lower())
        elif args.sort == "supplier":
            models.sort(key=lambda m: m.get("supplier", "").lower())
        elif args.sort == "context":
            def parse_ctx(c):
                s = str(c).lower().strip()
                if s.endswith("k"): return float(s[:-1] or 0) * 1000
                if s.endswith("m"): return float(s[:-1] or 0) * 1000000
                try: return float(s)
                except ValueError: return 0
            models.sort(key=lambda m: parse_ctx(m.get("context", "")))

    if not models:
        console.print("[yellow]No models found matching the criteria.[/yellow]")
        return

    run_list(models, verbose=args.verbose)

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

    # Show command
    parser_show = subparsers.add_parser("show", help="Show full config of a model by ID")
    parser_show.add_argument("identifier", help="The ID of the model to show")
    parser_show.set_defaults(func=cmd_show)

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
    parser_list.add_argument("ids", nargs="*", help="Optional list of model IDs to show")
    parser_list.add_argument("-p", "--provider", help="Filter by provider")
    parser_list.add_argument("-s", "--supplier", help="Filter by supplier")
    parser_list.add_argument("-t", "--tag", help="Filter by tag")
    parser_list.add_argument("--sort", choices=["name", "supplier", "context"], help="Sort models by name, supplier, or context")
    parser_list.add_argument("-v", "--verbose", action="store_true", help="Show full model information")
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

    # Web command
    parser_web = subparsers.add_parser("web", help="Start the web UI dashboard")
    parser_web.add_argument("-p", "--port", type=int, default=6565, help="Port to run the web UI on (default: 6565)")
    parser_web.set_defaults(func=cmd_web)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Execute the appropriate function
    args.func(args)

if __name__ == "__main__":
    main()
