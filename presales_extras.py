
from __future__ import annotations
import io, zipfile, json
from pathlib import Path
from datetime import datetime
from typing import Set

from flask import Blueprint, current_app, render_template, send_from_directory, send_file, abort

bp = Blueprint("extras", __name__)

OUT_DOCX = Path("output-docx")
OUT_DOCX.mkdir(parents=True, exist_ok=True)
BASE = Path("generated/submissions")
BASE.mkdir(parents=True, exist_ok=True)

def _paths(sid: str):
    return (BASE / f"{sid}.json", BASE / f"{sid}-ctx.json")

def load_data(sid: str) -> dict:
    data_path, _ = _paths(sid)
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    return {}

def load_ctx(sid: str) -> dict | None:
    _, ctx_path = _paths(sid)
    if ctx_path.exists():
        return json.loads(ctx_path.read_text(encoding="utf-8"))
    return None

def save_ctx(sid: str, ctx: dict) -> None:
    _, ctx_path = _paths(sid)
    ctx_path.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")

def build_ctx_from_fs(sid: str, data: dict | None = None) -> dict:
    present = {p.name for p in OUT_DOCX.glob("*.docx")}
    known = ["SOW.docx","HLD.docx","LOE.docx","PDG.docx","LLD.docx","ATP.docx","WBS.docx"]
    deliverables = [{"filename": n, "title": n.rsplit(".",1)[0]} for n in known if n in present]
    return {
        "sid": sid,
        "submitted_at": datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "data": data or {},
        "deliverables": deliverables,
        "docx_dir": str(OUT_DOCX),
    }

@bp.app_context_processor
def inject_has_endpoint():
    def has_endpoint(name: str) -> bool:
        return name in current_app.view_functions
    return {"has_endpoint": has_endpoint}

@bp.route("/presales/view/<sid>")
def presales_view(sid: str):
    data = load_data(sid)
    ctx = load_ctx(sid)
    if ctx is None:
        ctx = build_ctx_from_fs(sid, data)
        save_ctx(sid, ctx)
    ctx.setdefault("sid", sid)
    return render_template("presales_submitted.html",
                           data=data, submit_id=sid, ctx=ctx, now=datetime.utcnow())

@bp.route("/download/<sid>/<path:filename>")
def download_deliverable(sid: str, filename: str):
    ctx = load_ctx(sid) or build_ctx_from_fs(sid, load_data(sid))
    allowed: Set[str] = {d.get("filename") for d in ctx.get("deliverables", []) if isinstance(d, dict)}
    path = OUT_DOCX / filename
    if filename not in allowed or not path.exists():
        abort(404)
    return send_from_directory(OUT_DOCX, filename, as_attachment=True)

@bp.route("/presales/zip/<sid>")
def presales_zip(sid: str):
    ctx = load_ctx(sid) or build_ctx_from_fs(sid, load_data(sid))
    files = [d.get("filename") for d in ctx.get("deliverables", []) if isinstance(d, dict) and d.get("filename")]
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            p = OUT_DOCX / name
            if p.exists():
                z.write(p, arcname=name)
    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=f"{sid}-docs.zip")
