
from flask import Blueprint, render_template
from pathlib import Path
import json

history_bp = Blueprint("history", __name__)

DATA_DIR = Path("generated/submissions")

@history_bp.route("/presales/view/<sid>")
def presales_view(sid):
    """Legacy-compatible history/detail route.
    Loads ctx from generated/submissions/<sid>-ctx.json and passes it to the template.
    Falls back gracefully if ctx is missing.
    """
    ctx_path = DATA_DIR / f"{sid}-ctx.json"
    ctx = None
    if ctx_path.exists():
        ctx = json.loads(ctx_path.read_text())

    # Also pass a simple 'submission' dict for older templates that expect it
    submission = {"sid": sid, "ctx": ctx}

    return render_template(
        "presales_submitted.html",
        sid=sid,
        ctx=ctx,
        submission=submission,
    )
