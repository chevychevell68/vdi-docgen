
from flask import Blueprint, send_file, redirect, url_for, flash
from pathlib import Path
import json

from services import docgen, wbs
from services.schema import build_context

# This blueprint duplicates the outputs endpoints in case the original isn't registered.
# It also supports legacy submissions that only saved <sid>-raw.json by rebuilding ctx on the fly.

rescue_outputs_bp = Blueprint("rescue_outputs", __name__)

DATA_DIR = Path("generated/submissions")
OUT_DIR  = Path("generated/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _load_ctx_any(sid: str):
    # Try new ctx first
    p = DATA_DIR / f"{sid}-ctx.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    # Legacy: rebuild from raw if available
    rawp = DATA_DIR / f"{sid}-raw.json"
    if rawp.exists():
        try:
            raw = json.loads(rawp.read_text())
            return build_context(raw)
        except Exception:
            pass
    return None

def _ensure_ctx_or_redirect(sid):
    ctx = _load_ctx_any(sid)
    if not ctx:
        flash("Submission not found or missing context.")
        return None, redirect(url_for("presales.presales_new"))
    return ctx, None

@rescue_outputs_bp.route("/outputs/<sid>/sow.docx")
def sow_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("sow.md.j2", ctx, OUT_DIR, f"sow-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"sow-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/hld.docx")
def hld_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("hld.md.j2", ctx, OUT_DIR, f"hld-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"hld-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/lld.docx")
def lld_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("lld.md.j2", ctx, OUT_DIR, f"lld-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"lld-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/runbook.docx")
def runbook_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("runbook.md.j2", ctx, OUT_DIR, f"runbook-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"runbook-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/pdg.docx")
def pdg_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("pdg.md.j2", ctx, OUT_DIR, f"pdg-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"pdg-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/atp.docx")
def atp_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("atp.md.j2", ctx, OUT_DIR, f"atp-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"atp-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/adoption_plan.docx")
def adoption_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("adoption_plan.md.j2", ctx, OUT_DIR, f"adoption-plan-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"adoption-plan-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/loe.docx")
def loe_docx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = docgen.render_docx("loe.md.j2", ctx, OUT_DIR, f"loe-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"loe-{sid}.docx")

@rescue_outputs_bp.route("/outputs/<sid>/wbs.xlsx")
def wbs_xlsx(sid: str):
    ctx, r = _ensure_ctx_or_redirect(sid)
    if r: return r
    path = wbs.build_wbs(ctx, OUT_DIR, f"wbs-{sid}.xlsx")
    return send_file(path, as_attachment=True, download_name=f"wbs-{sid}.xlsx")

@rescue_outputs_bp.route("/outputs/<sid>/bundle.zip")
def bundle_zip(sid: str):
    ctx = _load_ctx_any(sid) or {}
    sel = ctx.get("deliverables", {
        "sow": True, "hld": True, "lld": True, "runbook": True, "pdg": True,
        "loe_wbs": True, "atp": True, "adoption_plan": True
    })

    paths = []
    if sel.get("sow", True):
        paths.append(docgen.render_docx("sow.md.j2", ctx, OUT_DIR, f"sow-{sid}.docx"))
    if sel.get("hld", True):
        paths.append(docgen.render_docx("hld.md.j2", ctx, OUT_DIR, f"hld-{sid}.docx"))
    if sel.get("lld", True):
        paths.append(docgen.render_docx("lld.md.j2", ctx, OUT_DIR, f"lld-{sid}.docx"))
    if sel.get("runbook", True):
        paths.append(docgen.render_docx("runbook.md.j2", ctx, OUT_DIR, f"runbook-{sid}.docx"))
    if sel.get("pdg", True):
        paths.append(docgen.render_docx("pdg.md.j2", ctx, OUT_DIR, f"pdg-{sid}.docx"))
    if sel.get("atp", True):
        paths.append(docgen.render_docx("atp.md.j2", ctx, OUT_DIR, f"atp-{sid}.docx"))
    if sel.get("adoption_plan", True):
        paths.append(docgen.render_docx("adoption_plan.md.j2", ctx, OUT_DIR, f"adoption-plan-{sid}.docx"))
    if sel.get("loe_wbs", True):
        paths.append(docgen.render_docx("loe.md.j2", ctx, OUT_DIR, f"loe-{sid}.docx"))
        paths.append(wbs.build_wbs(ctx, OUT_DIR, f"wbs-{sid}.xlsx"))

    # Include attachments if your app stored them
    attach_dir = DATA_DIR / f"{sid}-attachments"
    if attach_dir.exists():
        for p in attach_dir.glob("*"):
            paths.append(p)

    zip_path = OUT_DIR / f"bundle-{sid}.zip"
    zip_path = docgen.zip_files(paths, zip_path)
    return send_file(zip_path, as_attachment=True, download_name=f"bundle-{sid}.zip")
