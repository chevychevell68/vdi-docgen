
# ctxio.py — context I/O utilities for VDI-DocGen
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

BASE = Path("generated/submissions")
OUT_DOCX = Path("output-docx")

# The filenames the UI expects
KNOWN_DOCS = [
    "SOW.docx", "HLD.docx", "LOE.docx", "PDG.docx",
    "LLD.docx", "ATP.docx", "WBS.docx",
]

def _paths(sid: str):
    BASE.mkdir(parents=True, exist_ok=True)
    return (
        BASE / f"{sid}.json",
        BASE / f"{sid}-ctx.json",
    )

def load_data(sid: str) -> dict:
    data_path, _ = _paths(sid)
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    return {}

def save_ctx(sid: str, ctx: dict) -> None:
    _, ctx_path = _paths(sid)
    ctx_path.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")

def load_ctx(sid: str) -> dict | None:
    _, ctx_path = _paths(sid)
    if ctx_path.exists():
        return json.loads(ctx_path.read_text(encoding="utf-8"))
    return None

def build_ctx_from_fs(sid: str, data: dict | None = None) -> dict:
    """Scan output-docx for known deliverables and build a ctx dict."""
    OUT_DOCX.mkdir(parents=True, exist_ok=True)
    deliverables = []
    present = {p.name for p in OUT_DOCX.glob("*.docx")}
    for name in KNOWN_DOCS:
        if name in present:
            deliverables.append({"filename": name, "title": name.rsplit(".", 1)[0]})
    ctx = {
        "sid": sid,
        "submitted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "data": data or {},
        "deliverables": deliverables,
        "docx_dir": str(OUT_DOCX),
    }
    return ctx
