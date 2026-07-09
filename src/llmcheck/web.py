import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import add_model, edit_model, load_models, remove_model
from .checker import PING_MESSAGES, check_single_model

app = FastAPI(title="llmcheck Web UI")

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"


# ── Pydantic models ──────────────────────────────────────────────────────────


class ModelCreate(BaseModel):
    name: str
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    supplier: str = ""
    context: str = ""
    tags: str = ""
    display_id: str = ""


class ModelUpdate(BaseModel):
    name: str = ""
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    supplier: str = ""
    context: str = ""
    tags: str = ""
    display_id: str = ""


# ── REST endpoints ────────────────────────────────────────────────────────────


@app.get("/api/models")
def api_list_models(supplier: str = "", tag: str = ""):
    models = load_models()
    if supplier:
        models = [m for m in models if m.get("supplier", "").lower() == supplier.lower()]
    if tag:
        models = [
            m for m in models
            if tag.lower() in [t.strip() for t in m.get("tags", "").lower().split(",")]
        ]
    return models


@app.get("/api/models/{model_id}")
def api_get_model(model_id: str):
    models = load_models()
    target = next((m for m in models if m.get("_id") == model_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return target


@app.post("/api/models", status_code=201)
def api_add_model(body: ModelCreate):
    add_model(
        name=body.name,
        provider=body.provider,
        model_name=body.model,
        api_key=body.api_key,
        base_url=body.base_url or None,
        supplier=body.supplier or None,
        context=body.context or None,
        tags=body.tags or None,
        display_id=body.display_id or None,
    )
    # Return the newly-added model
    models = load_models()
    return models[-1] if models else {}


@app.put("/api/models/{model_id}")
def api_edit_model(model_id: str, body: ModelUpdate):
    models = load_models()
    target = next((m for m in models if m.get("_id") == model_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    updates = {}
    if body.name:
        updates["name"] = body.name
    if body.provider:
        updates["provider"] = body.provider
    if body.model:
        updates["model"] = body.model
    if body.supplier:
        updates["supplier"] = body.supplier
    updates["context"] = body.context
    # Always write tags (allows clearing)
    updates["tags"] = body.tags
    if body.api_key:
        updates["api_key"] = body.api_key
    if body.base_url is not None:
        updates["base_url"] = body.base_url if body.base_url.lower() != "none" else ""
    if body.display_id is not None:
        updates["display_id"] = body.display_id

    if not edit_model(model_id, updates):
        raise HTTPException(status_code=500, detail="Failed to update model")

    models = load_models()
    return next((m for m in models if m.get("_id") == model_id), {})


@app.delete("/api/models/{model_id}")
def api_remove_model(model_id: str):
    if not remove_model(model_id):
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return {"ok": True}


# ── SSE check endpoint ────────────────────────────────────────────────────────


def _run_checks_threaded(models_to_check: list, result_queue: queue.Queue):
    """Run checks in background threads, one per supplier/provider group."""
    groups: dict[str, list] = {}
    for m in models_to_check:
        key = str(m.get("supplier") or m.get("provider") or m.get("_id")).strip().lower()
        groups.setdefault(key, []).append(m)

    def check_group(group):
        for m in group:
            result_queue.put(check_single_model(m, PING_MESSAGES, verbose=True))

    threads = [threading.Thread(target=check_group, args=(g,), daemon=True) for g in groups.values()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    result_queue.put(None)  # sentinel


@app.get("/api/check")
def api_check_all():
    """Stream real-time check results via Server-Sent Events."""
    models = load_models()
    return _sse_check(models)


@app.get("/api/check/{model_id}")
def api_check_one(model_id: str):
    """Stream check result for a single model via SSE."""
    models = load_models()
    targets = [m for m in models if m.get("_id") == model_id]
    if not targets:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return _sse_check(targets)


def _sse_check(models: list) -> StreamingResponse:
    result_queue: queue.Queue = queue.Queue()

    thread = threading.Thread(
        target=_run_checks_threaded, args=(models, result_queue), daemon=True
    )
    thread.start()

    def event_generator():
        total = len(models)
        received = 0
        while received < total:
            try:
                result = result_queue.get(timeout=30)
            except queue.Empty:
                break
            if result is None:
                break

            payload = {
                "id": result["id"],
                "name": result["name"],
                "tags": result["tags"],
                "context": result["context"],
                "supplier": result["supplier"],
                "provider": result["provider"],
                "api_key": result["api_key"],
                "model": result["model"],
                "status": "ok" if result["status"] == "✅" else "error",
                "latency": result["latency"],
                "error": result["error"],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            received += 1

        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Serve SPA ────────────────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
