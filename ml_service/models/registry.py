"""Filesystem model registry with versioning + metrics tracking.

Layout::

    <MODEL_DIR>/<name>/v1/{model.joblib, meta.json}
    <MODEL_DIR>/<name>/v2/...
    <MODEL_DIR>/<name>/latest.txt   -> "v2"

`meta.json` carries feature columns, metrics (RMSE / F1 / accuracy), class
labels, and any extra scoring info needed at inference.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib


class ModelRegistry:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _model_dir(self, name: str) -> Path:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _next_version(self, name: str) -> str:
        d = self._model_dir(name)
        versions = [int(p.name[1:]) for p in d.glob("v*") if p.name[1:].isdigit()]
        return f"v{max(versions, default=0) + 1}"

    def save(self, name: str, model: Any, metrics: dict, meta: dict | None = None) -> str:
        version = self._next_version(name)
        vdir = self._model_dir(name) / version
        vdir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, vdir / "model.joblib")
        full_meta = {
            "name": name,
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            **(meta or {}),
        }
        (vdir / "meta.json").write_text(json.dumps(full_meta, indent=2))
        (self._model_dir(name) / "latest.txt").write_text(version)
        return version

    def load_latest(self, name: str) -> tuple[Any | None, dict | None]:
        latest_file = self._model_dir(name) / "latest.txt"
        if not latest_file.exists():
            return None, None
        version = latest_file.read_text().strip()
        vdir = self._model_dir(name) / version
        try:
            model = joblib.load(vdir / "model.joblib")
            meta = json.loads((vdir / "meta.json").read_text())
            return model, meta
        except Exception:
            return None, None

    def info(self) -> dict:
        out: dict[str, Any] = {}
        for d in sorted(self.root.glob("*")):
            if not d.is_dir():
                continue
            latest = (d / "latest.txt")
            versions = sorted(p.name for p in d.glob("v*") if p.is_dir())
            out[d.name] = {
                "latest": latest.read_text().strip() if latest.exists() else None,
                "versions": versions,
            }
        return out
