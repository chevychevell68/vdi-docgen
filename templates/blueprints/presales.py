
from flask import Blueprint, request, render_template, redirect, url_for, flash
from services.schema import build_context
import json, uuid, time
from pathlib import Path

presales_bp = Blueprint("presales", __name__)

DATA_DIR = Path("generated/submissions")
DATA_DIR.mkdir(parents=True, exist_ok=True)

@presales_bp.route("/presales/new", methods=["GET", "POST"])
def presales_new():
    if request.method == "POST":
        raw = request.form.to_dict(flat=True)
        ctx = build_context(raw)

        sid = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
        (DATA_DIR / f"{sid}-raw.json").write_text(json.dumps(raw, indent=2))
        (DATA_DIR / f"{sid}-ctx.json").write_text(json.dumps(ctx, indent=2))

        flash("Presales submitted.")
        return redirect(url_for("presales.presales_summary", sid=sid))

    # Render your existing form template; update name if different
    return render_template("presales_form.html")

@presales_bp.route("/presales/<sid>")
def presales_summary(sid: str):
    ctx_path = DATA_DIR / f"{sid}-ctx.json"
    if not ctx_path.exists():
        flash("Submission not found.")
        return redirect(url_for("presales.presales_new"))
    ctx = json.loads(ctx_path.read_text())
    return render_template("presales_submitted.html", ctx=ctx, sid=sid)
