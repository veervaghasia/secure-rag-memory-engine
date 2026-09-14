"""
ingestion/experiment_registry.py

Manages recording, updating, and retrieving experiment metadata in 
a lightweight data/experiments.json registry file.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from config import config

def _load_registry() -> Dict[str, Any]:
    """
    Helper to read the JSON registry file from disk if it exists.
    """
    registry_path = config.experiment.registry_path
    if not os.path.exists(registry_path):
        return {"experiments": {}}

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [ExperimentRegistry] Failed to read registry at '{registry_path}' ({e}). Starting fresh.")
        return {"experiments": {}}

def _save_registry(data: Dict[str, Any]) -> None:
    """
    Helper to write the dictionary back to disk.
    """
    registry_path = config.experiment.registry_path
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def register_experiment(description: str = "", status: str = "active") -> Dict[str, Any]:
    """
    Logs the current active configuration settings as an experiment 
    record inside data/experiments.json.
    """
    data = _load_registry()
    experiments = data.setdefault("experiments", {})

    exp_id = config.experiment.experiment_id

    if exp_id in experiments:
        print(f"ℹ️ [ExperimentRegistry] Experiment '{exp_id}' already exists.")
        return experiments[exp_id]

    now = datetime.now().isoformat()

    record = {
        "experiment_id": exp_id,
        "created_at": now,
        "updated_at": now,
        "status": status, # "active" | "archived" | "purged"
        "description": (description or f"Experiment run for {exp_id}"),
        "chunk_size": config.chunking.chunk_size,
        "chunk_overlap": config.chunking.chunk_overlap,
        "embedding_model": config.vector_store.embedding_model,
        "chroma_collection": config.vector_store.collection_name,
        "bm25_index_path": config.bm25.index_path,
        "manifest_path": config.experiment.manifest_path
    }

    experiments[exp_id] = record
    _save_registry(data)

    print(f"✅ [ExperimentRegistry] Registered experiment '{exp_id}' in '{config.experiment.registry_path}'.")
    return record

def update_experiment_description(experiment_id: str, new_description: str) -> bool:
    """
    Updates the description field for an existing registered experiment 
    without altering configs.
    """
    data = _load_registry()
    experiments = data.get("experiments", {})

    if experiment_id not in experiments:
        print(f"❌ [ExperimentRegistry] Experiment ID '{experiment_id}' not found in registry.")
        print(f"💡 Use list_experiments() or check '{config.experiment.registry_path}' to see existing IDs.")
        return False

    experiments[experiment_id]["description"] = new_description
    experiments[experiment_id]["updated_at"] = datetime.now().isoformat()
    _save_registry(data)
    print(f"✅ [ExperimentRegistry] Updated description for '{experiment_id}'.")
    return True

def update_experiment_status(experiment_id: str, new_status: str) -> bool:
    """
    Updates the operational status (e.g., 'active', 'archived', 'purged') for an experiment.
    """
    data = _load_registry()
    experiments = data.get("experiments", {})

    if experiment_id not in experiments:
        print(f"❌ [ExperimentRegistry] Experiment ID '{experiment_id}' not found in registry.")
        return False

    experiments[experiment_id]["status"] = new_status
    experiments[experiment_id]["updated_at"] = datetime.now().isoformat()
    _save_registry(data)
    print(f"✅ [ExperimentRegistry] Updated status for '{experiment_id}' to '{new_status}'.")
    return True

def list_experiments() -> Dict[str, Any]:
    """
    Retrieves all previously registered experiment metadata entries.
    """
    data = _load_registry()
    experiments = data.get("experiments", {})
    if not experiments:
        print(f"ℹ️ [ExperimentRegistry] No experiments registered yet in '{config.experiment.registry_path}'.Run ingest.py to register one!")
    return experiments
    