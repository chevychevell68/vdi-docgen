# app.py
from __future__ import annotations

import io
import json
import math
import os
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    render_template_string,
    request,
    send_file,
    url_for,
)

# Optional Word support (pip install python-docx)
try:
    from docx import Document  # type: ignore
except Exception:
    Document = None

# --------------------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Prefer persistent disk on Render; fall back locally
STORAGE_DIR_CANDIDATES = ["/var/data", "./data"]
for _d in STORAGE_DIR_CANDIDATES:
    try:
        os.makedirs(_d, exist_ok=True)
        STORAGE_DIR = _d
        break
    except Exception:
        continue
else:
    STORAGE_DIR = "."

ENTRIES_PATH = os.path.join(STORAGE_DIR, "entries.jsonl")


# --------------------------------------------------------------------------------------
# Persistence helpers (JSONL append-only)
# --------------------------------------------------------------------------------------
def _now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _gen_entry_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _safe_read_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


def _write_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def append_entry(payload: Dict[str, Any]) -> str:
    """Append a submission to entries.jsonl and return an entry_id."""
    entry = dict(payload)  # shallow copy
    entry_id = _gen_entry_id()
    entry["entry_id"] = entry_id
    entry["submitted_utc"] = entry.get("submitted_utc") or _now_utc_str()
    _write_line(ENTRIES_PATH, json.dumps(entry, ensure_ascii=False))
    return entry_id


def read_all_entries() -> List[Dict[str, Any]]:
    lines = _safe_read_lines(ENTRIES_PATH)
    out: List[Dict[str, Any]] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return sorted(out, key=lambda x: x.get("entry_id", ""), reverse=True)


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    for e in read_all_entries():
        if e.get("entry_id") == entry_id:
            return e
    return None


# --------------------------------------------------------------------------------------
# Home (PDG removed; Predeploy renamed; History added)
# --------------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VDI Tools</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container" style="max-width: 920px;">
    <h1 class="mb-4">VDI Discovery Tools</h1>
    <div class="list-group">
      <a class="list-group-item list-group-item-action" href="{{ url_for('presales') }}">Presales Discovery Form</a>
      <a class="list-group-item list-group-item-action" href="{{ url_for('predeploy') }}">Pre-Deployment Guide</a>
      <a class="list-group-item list-group-item-action" href="{{ url_for('history') }}">History (Past Submissions)</a>
    </div>
    <div class="text-muted mt-4">Home v2.4 — Storage: <code>{{ storage_dir }}</code></div>
  </div>
</body>
</html>""",
        storage_dir=STORAGE_DIR,
    )


# --------------------------------------------------------------------------------------
# Presales form (GET/POST)
# --------------------------------------------------------------------------------------
@app.route("/presales", methods=["GET", "POST"])
def presales():
    """
    GET: render form
    POST: validate + compute + show submitted summary + persist entry
    """
    # Try to render your Jinja template if present; otherwise fallback
    def _render_presales_form(form: Dict[str, Any]):
        try:
            return render_template("presales_form.html", form=form)
        except Exception:
            # Minimal fallback form
            return render_template_string(
                """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Presales (Fallback)</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-4">
<div class="container" style="max-width: 920px;">
  <h1>Presales (Fallback)</h1>
  <p class="text-muted">Your <code>presa
