# presales.py — Blueprint with additive routes that use Pandoc (no app.py edits required)
from __future__ import annotations
import json, os
from pathlib import Path
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_from_directory
from datetime import datetime

from pandoc_gen import generate_phase1_docs

presales_bp = Blueprint("presales_bp", __name__)

def _load_submission(root: Path, submit_id: str):
    p = (root / f"{submit_id}.json").resolve()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

@presales_bp.route("/tools/generate/<submit_id>", methods=["POST", "GET"])
def tools_generate(submit_id: str):
    """Generate SOW/HLD/LOE into output-docx/<sid>/ using Pandoc and redirect back to results page."""
    output_dir = Path(current_app.config.get("OUTPUT_DIR", "output"))
    docx_root  = Path(current_app.config.get("DOCX_DIR", "output-docx"))
    submit_dir = Path(current_app.config.get("SUBMIT_DIR", "submissions"))
    template_root = Path(current_app.template_folder or "templates") / "docgen"
    reference_docx = Path(os.getenv("PANDOC_REFERENCE_DOCX", "")).resolve() if os.getenv("PANDOC_REFERENCE_DOCX") else None

    docx_per_sid = docx_root / submit_id
    docx_per_sid.mkdir(parents=True, exist_ok=True)

    obj = _load_submission(submit_dir, submit_id)
    if not obj:
        flash("Submission not found.", "error")
        return redirect(url_for("history"))

    try:
        generate_phase1_docs(obj, docx_per_sid, template_root, reference_docx)
    except Exception as e:
        flash(f"Doc generation failed: {e}", "error")
        return redirect(url_for("presales_view", submit_id=submit_id))

    flash("Generated SOW, HLD, LOE via Pandoc.", "success")
    return redirect(url_for("presales_view", submit_id=submit_id))

@presales_bp.route("/tools/open/<submit_id>/<path:filename>", methods=["GET"])
def tools_open_generated(submit_id: str, filename: str):
    docx_root  = Path(current_app.config.get("DOCX_DIR", "output-docx"))
    path = (docx_root / submit_id / filename).resolve()
    if not path.exists():
        flash("File not found.", "error")
        return redirect(url_for("presales_view", submit_id=submit_id))
    return send_from_directory(path.parent, path.name, as_attachment=True)
