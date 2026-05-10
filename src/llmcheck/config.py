import os
import logging
from pathlib import Path
from dotenv import dotenv_values

# Suppress dotenv parse warnings (e.g., from litellm auto-loading unrelated .env files)
logging.getLogger('dotenv.main').setLevel(logging.ERROR)

CONFIG_FILE = Path.home() / ".llmcheck_env"

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
    
    sorted_models = []
    for idx in sorted(models.keys(), key=lambda x: int(x) if x.isdigit() else x):
        sorted_models.append(models[idx])
    return sorted_models

def add_model(name, provider, model_name, api_key, base_url=None, supplier=None, category=None):
    """Adds a new model configuration."""
    models = load_models()
    
    # Determine the next ID
    max_id = 0
    for m in models:
        try:
            m_id = int(m["_id"])
            if m_id > max_id:
                max_id = m_id
        except ValueError:
            pass
            
    next_id = max_id + 1
    prefix = f"MODEL_{next_id}_"
    
        f"",
        f"# Model Configuration for {name}",
        f'{prefix}NAME="{name}"',
        f'{prefix}PROVIDER="{provider}"',
        f'{prefix}MODEL="{model_name}"',
        f'{prefix}API_KEY="{api_key}"'
    ]
    if base_url:
        lines.append(f'{prefix}BASE_URL="{base_url}"')
    if supplier:
        lines.append(f'{prefix}SUPPLIER="{supplier}"')
    if category:
        lines.append(f'{prefix}CATEGORY="{category}"')
        
    with open(CONFIG_FILE, "a") as f:
        f.write("\n".join(lines) + "\n")

def remove_model(identifier):
    """Removes a model configuration by alias or ID."""
    if not CONFIG_FILE.exists():
        return False
        
    models = load_models()
    target_id = None
    for m in models:
        if m.get("_id") == str(identifier) or m.get("alias", "").lower() == str(identifier).lower():
            target_id = m["_id"]
            break
            
    if not target_id:
        return False
        
    prefix = f"MODEL_{target_id}_"
    
    # Read lines and rewrite excluding the target prefix
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
        
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if not line.strip().startswith(prefix):
                f.write(line)
                
    return True

def edit_model(identifier, updates):
    """Edits an existing model configuration by alias or ID. updates is a dict of fields to update."""
    if not CONFIG_FILE.exists():
        return False
        
    models = load_models()
    target_id = None
    target_model = None
    for m in models:
        if m.get("_id") == str(identifier) or m.get("alias", "").lower() == str(identifier).lower():
            target_id = m["_id"]
            target_model = m
            break
            
    if not target_id:
        return False
        
    prefix = f"MODEL_{target_id}_"
    
    for k, v in updates.items():
        target_model[k] = v
            
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    block_inserted = False
    
    for line in lines:
        if line.strip().startswith(prefix):
            if not block_inserted:
                new_block = [
                    f'{prefix}NAME="{target_model.get("name", "")}"\n',
                    f'{prefix}PROVIDER="{target_model.get("provider", "")}"\n',
                    f'{prefix}MODEL="{target_model.get("model", "")}"\n',
                    f'{prefix}API_KEY="{target_model.get("api_key", "")}"\n',
                ]
                if target_model.get("base_url"):
                    new_block.append(f'{prefix}BASE_URL="{target_model["base_url"]}"\n')
                if target_model.get("supplier"):
                    new_block.append(f'{prefix}SUPPLIER="{target_model["supplier"]}"\n')
                if target_model.get("category"):
                    new_block.append(f'{prefix}CATEGORY="{target_model["category"]}"\n')
                new_lines.extend(new_block)
                block_inserted = True
        else:
            new_lines.append(line)
            
    with open(CONFIG_FILE, "w") as f:
        f.writelines(new_lines)
        
    return True
