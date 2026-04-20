from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from src.classification.paragraph_classifier import (
    ClassificationConfig,
    run_classification_pipeline,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

router = APIRouter(prefix="/upload", tags=["upload"])

METHODS_CONFIG = {
    "vocab": {
        "method": "vocab",
        "params": {},
    },
    "doc_word_topic": {
        "method": "doc_word_topic",
        "params": {},
    },
    "ministry_embedding": {
        "method": "ministry_embedding",
        "params": {"embedding_file": "data/embeddings/ministry_embeddings.json"},
    },
    "ministry_embedding_v1": {
        "method": "ministry_embedding",
        "params": {"embedding_file": "data/embeddings/ministry_embeddings1.json"},
    },
    "ministry_embedding_v2": {
        "method": "ministry_embedding",
        "params": {"embedding_file": "data/embeddings/ministry_embeddings2.json"},
    },
    "ministry_embedding_multi": {
        "method": "ministry_embedding_multi",
        "params": {
            "aggregation": "topk",
            "top_k": 3,
            "embedding_file": "data/embeddings/ministry_embeddings3.json",
        },
    },
    "topic_embedding": {
        "method": "topic_embedding",
        "params": {},
    },
}

TASK_STORE: Dict[str, Dict[str, Any]] = {}
TASK_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_update_task(task_id: str, **updates: Any) -> None:
    with TASK_LOCK:
        task = TASK_STORE.get(task_id)
        if task is None:
            return
        task.update(updates)
        task["updated_at"] = _utc_now()


def _build_config(pdf_path: str, method_name: str, method_config: Dict[str, Any]) -> ClassificationConfig:
    cfg = ClassificationConfig(
        pdf_path=pdf_path,
        method=method_config["method"],
        topic_state_file="data/topic_modeling/state.csv",
        ministry_profiles_dir="data/ministry_profiles",
        stopword_files=(
            "data/stopwords/GBparl_stopwords-empirical.txt",
            "data/stopwords/stopwords.txt",
        ),
        validator_vocab_path="data/vocabulary/parliament_vocab.txt",
        vocab_file="data/vocabulary/ministry_tfidf_vocab.json",
        ministry_embedding_file=method_config["params"].get(
            "embedding_file", "data/embeddings/ministry_embeddings.json"
        ),
        topic_embedding_file="data/embeddings/topic_embeddings.json",
        topic_mapping_file="data/topic_modeling/top_topics_per_ministry.csv",
        model_name="all-MiniLM-L6-v2",
        model_cache_folder="models",
    )

    if "aggregation" in method_config["params"]:
        cfg.primary_params = {
            "aggregation": method_config["params"]["aggregation"],
            "top_k": method_config["params"]["top_k"],
        }

    return cfg


def _process_document_task(task_id: str, pdf_path: str) -> None:
    _safe_update_task(task_id, status="processing", completed_methods=0, total_methods=len(METHODS_CONFIG))

    method_outputs: Dict[str, Any] = {}
    completed_count = 0
    try:
        for method_name, method_config in METHODS_CONFIG.items():
            cfg = _build_config(pdf_path=pdf_path, method_name=method_name, method_config=method_config)
            try:
                output = run_classification_pipeline(cfg)
                # keep only follownig keys in output to reduce response size- num_paragraphs, results
                method_outputs[method_name] = {key: output[key] for key in ['num_paragraphs', 'results'] if key in output}
            except Exception as method_exc:
                method_outputs[method_name] = {
                    "error": f"{type(method_exc).__name__}: {method_exc}",
                }
            
            completed_count += 1
            _safe_update_task(task_id, completed_methods=completed_count)

        _safe_update_task(
            task_id,
            status="completed",
            result={
                "message": "results received",
                "outputs": method_outputs,
            },
        )
    except Exception as exc:
        _safe_update_task(
            task_id,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        try:
            Path(pdf_path).unlink(missing_ok=True)
        except OSError:
            pass


@router.get("/", response_class=HTMLResponse)
async def upload_page() -> HTMLResponse:
    static_dir = Path(__file__).parent.parent / "static"
    upload_html = static_dir / "upload.html"
    if not upload_html.exists():
        raise HTTPException(status_code=404, detail="upload.html not found")
    return HTMLResponse(content=upload_html.read_text(encoding="utf-8"))


@router.post("/", status_code=202)
async def handle_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    extension = Path(file.filename).suffix.lower()
    if extension != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    uploads_dir = Path("data/uploads/tmp")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    task_id = str(uuid.uuid4())
    temp_path = uploads_dir / f"{task_id}{extension}"
    content = await file.read()
    temp_path.write_bytes(content)

    with TASK_LOCK:
        TASK_STORE[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "file_name": file.filename,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "result": None,
            "error": None,
            "completed_methods": 0,
            "total_methods": len(METHODS_CONFIG),
        }

    background_tasks.add_task(_process_document_task, task_id, str(temp_path))
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Upload accepted. Processing started asynchronously.",
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    with TASK_LOCK:
        task = TASK_STORE.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        response = {
            "task_id": task["task_id"],
            "status": task["status"],
            "file_name": task["file_name"],
            "created_at": task["created_at"],
            "updated_at": task["updated_at"],
            "error": task.get("error"),
            "completed_methods": task.get("completed_methods", 0),
            "total_methods": task.get("total_methods", len(METHODS_CONFIG)),
        }
        if task["status"] == "completed":
            response["result"] = task.get("result")

        return response