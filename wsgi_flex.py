
# wsgi_flex.py — robust entrypoint with route diagnostics
from importlib import import_module
from flask import render_template, Response
from pathlib import Path
import json, sys

# 1) Import main app module
app_module = import_module("app")

# 2) Create app via factory or fall back to global
create_app = getattr(app_module, "create_app", None)
if callable(create_app):
    app = create_app()
else:
    app = getattr(app_module, "app", None)
    if app is None:
        raise RuntimeError("Neither create_app() nor a global 'app' found in app.py")

# 3) Best-effort import & register blueprints
def _try_register(mod_name, attr_name):
    try:
        mod = import_module(mod_name)
        bp = getattr(mod, attr_name, None)
        if bp is not None:
            try:
                app.register_blueprint(bp)
            except Exception as e:
                # Already registered or conflicting — that's fine.
                print(f"[wsgi_flex] Skipped registering {mod_name}:{attr_name} -> {e}", file=sys.stderr)
    except Exception as e:
        print(f"[wsgi_flex] Could not import {mod_name}: {e}", file=sys.stderr)

_try_register("blueprints.presales", "presales_bp")
_try_register("blueprints.outputs", "outputs_bp")
_try_register("blueprints.history", "history_bp")
# ALWAYS register rescue outputs to guarantee routes exist for legacy installs
_try_register("blueprints.rescue_outputs", "rescue_outputs_bp")

# 4) Patch legacy history endpoint to pass ctx (supports <sid> or <submit_id>)
def _patched_presales_view(*args, **kwargs):
    sid = None
    if args:
        sid = args[0]
    sid = sid or kwargs.get("sid") or kwargs.get("submit_id") or kwargs.get("id") or ""
    DATA_DIR = Path("generated/submissions")
    ctx = None
    p = DATA_DIR / f"{sid}-ctx.json"
    if p.exists():
        ctx = json.loads(p.read_text())
    submission = {"sid": sid, "ctx": ctx}
    # Prefer defensive template
    try:
        return render_template("presales_submitted_defensive.html", sid=sid, ctx=ctx, submission=submission)
    except Exception:
        return render_template("presales_submitted.html", sid=sid, ctx=ctx, submission=submission)

if "presales_view" in app.view_functions:
    app.view_functions["presales_view"] = _patched_presales_view
else:
    try:
        app.add_url_rule("/presales/view/<sid>", endpoint="presales_view", view_func=_patched_presales_view, methods=["GET"])
    except Exception:
        pass
    try:
        app.add_url_rule("/presales/view/<submit_id>", endpoint="presales_view", view_func=_patched_presales_view, methods=["GET"])
    except Exception:
        pass

# 5) Diagnostics: list all routes
@app.get("/_debug/routes")
def _debug_routes():
    rows = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        rows.append(f"{rule.rule}  ->  {rule.endpoint}  [{','.join(sorted(rule.methods - {'HEAD','OPTIONS'}))}]")
    return Response("\n".join(rows), mimetype="text/plain")

# Also print them on startup (to stderr so they show in logs)
try:
    print("[wsgi_flex] ROUTES:", file=sys.stderr)
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        print(f"  {rule.rule} -> {rule.endpoint}", file=sys.stderr)
except Exception:
    pass

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 5000, app, use_debugger=True, use_reloader=True)
