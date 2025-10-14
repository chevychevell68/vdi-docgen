
from flask import Blueprint, send_file, request, flash, redirect, url_for
from services import docgen, wbs
import json, zipfile
from pathlib import Path

outputs_bp = Blueprint("outputs", __name__)

DATA_DIR = Path("generated/submissions")
OUT_DIR  = Path("generated/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _load_ctx(sid: str):
    p = DATA_DIR / f"{sid}-ctx.json"
    return json.loads(p.read_text()) if p.exists() else None

@outputs_bp.route("/outputs/<sid>/sow.docx")
def sow_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("sow.md.j2", ctx, OUT_DIR, f"sow-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"sow-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/hld.docx")
def hld_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("hld.md.j2", ctx, OUT_DIR, f"hld-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"hld-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/lld.docx")
def lld_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("lld.md.j2", ctx, OUT_DIR, f"lld-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"lld-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/runbook.docx")
def runbook_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("runbook.md.j2", ctx, OUT_DIR, f"runbook-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"runbook-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/pdg.docx")
def pdg_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("pdg.md.j2", ctx, OUT_DIR, f"pdg-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"pdg-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/atp.docx")
def atp_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("atp.md.j2", ctx, OUT_DIR, f"atp-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"atp-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/adoption_plan.docx")
def adoption_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("adoption_plan.md.j2", ctx, OUT_DIR, f"adoption-plan-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"adoption-plan-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/loe.docx")
def loe_docx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = docgen.render_docx("loe.md.j2", ctx, OUT_DIR, f"loe-{sid}.docx")
    return send_file(path, as_attachment=True, download_name=f"loe-{sid}.docx")

@outputs_bp.route("/outputs/<sid>/wbs.xlsx")
def wbs_xlsx(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    path = wbs.build_wbs(ctx, OUT_DIR, f"wbs-{sid}.xlsx")
    return send_file(path, as_attachment=True, download_name=f"wbs-{sid}.xlsx")

@outputs_bp.route("/outputs/<sid>/bundle.zip")
def bundle_zip(sid: str):
    ctx = _load_ctx(sid)
    if not ctx:
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))

    sel = ctx.get("deliverables", {})
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

    # If you save file uploads per submission (e.g., DATA_DIR/sid-attachments/*), include them:
    attach_dir = DATA_DIR / f"{sid}-attachments"
    if attach_dir.exists():
        for p in attach_dir.glob("*"):
            paths.append(p)

    zip_path = OUT_DIR / f"bundle-{sid}.zip"
    zip_path = docgen.zip_files(paths, zip_path)
    return send_file(zip_path, as_attachment=True, download_name=f"bundle-{sid}.zip")
