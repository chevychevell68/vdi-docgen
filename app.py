import os
import io
import json
import math
import base64
import zipfile
import datetime as dt
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, current_app

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ---------- Inject safe helpers for Jinja ----------
def _fmt_bool(v):
    return "Yes" if str(v).lower() in {"1", "true", "yes", "on"} else "No"


def _none_to_empty(v):
    return "" if v is None else v


def _safe_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _safe_float(v, default=0.0):
    try:
        return float(str(v).strip())
    except Exception:
        return default


def _lines(s):
    if not s:
        return []
    return [line.rstrip() for line in str(s).splitlines()]


app.jinja_env.filters["fmt_bool"] = _fmt_bool
app.jinja_env.filters["none_to_empty"] = _none_to_empty
app.jinja_env.filters["lines"] = _lines

# Provide `has_endpoint(name)` to templates
@app.context_processor
def inject_helpers():
    def has_endpoint(name: str) -> bool:
        try:
            return name in current_app.view_functions
        except Exception:
            return False
    return dict(has_endpoint=has_endpoint)

# -------------------- Constants / Env --------------------
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
DELIV_DIR = OUTPUT_DIR / "deliverables"
DOCX_DIR = Path(os.getenv("DOCX_DIR", "output-docx"))
EXPORTS_DIR = OUTPUT_DIR / "exports"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "").strip()  # e.g., "owner/repo"
DEFAULT_BRANCH = os.getenv("DEFAULT_BRANCH", "main").strip()

for d in (OUTPUT_DIR, DELIV_DIR, DOCX_DIR, EXPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# -------------------- GitHub REST helpers --------------------
def github_get_file_sha(repo_owner: str, repo_name: str, path: str, branch: str):
    if not (GITHUB_TOKEN and repo_owner and repo_name and path and branch):
        return None
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}?ref={branch}"
    req = Request(url, headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"})
    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("sha")
    except HTTPError as e:
        if e.code == 404:
            return None
        return None
    except URLError:
        return None
    except Exception:
        return None


def github_upsert_file(repo_owner: str, repo_name: str, branch: str, path: str, content_bytes: bytes, commit_msg: str) -> bool:
    """Create or update a file via GitHub REST API."""
    if not (GITHUB_TOKEN and repo_owner and repo_name and branch and path):
        return False
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"
    body = {
        "message": commit_msg,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch,
    }
    # If file exists, include its sha
    existing_sha = github_get_file_sha(repo_owner, repo_name, path, branch)
    if existing_sha:
        body["sha"] = existing_sha

    data = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req) as resp:
            _ = resp.read()
        return True
    except Exception:
        return False


def push_export_to_github(owner_repo: str, branch: str, rel_path: str, content: bytes, commit_msg: str) -> bool:
    if not owner_repo:
        return False
    try:
        owner, repo = owner_repo.split("/", 1)
    except ValueError:
        return False
    return github_upsert_file(owner, repo, branch, rel_path, content, commit_msg)


# -------------------- Content helpers --------------------
def _coerce_bool(val) -> bool:
    return str(val).strip().lower() in {"1", "y", "yes", "true", "on"}


def _safe_getlist(form, key: str):
    try:
        return [v for v in form.getlist(key) if str(v).strip()]
    except Exception:
        return []


def _now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


# -------------------- Routes --------------------
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/predeploy")
def predeploy():
    return render_template("predeploy.html")


@app.get("/history")
def history():
    # Show prior exported deliverables
    md_files = sorted(DELIV_DIR.glob("*.md"))
    docx_files = sorted(DOCX_DIR.glob("*.docx"))
    return render_template(
        "history.html",
        md_files=[f.name for f in md_files],
        docx_files=[f.name for f in docx_files],
    )


@app.get("/checklist")
def checklist():
    return render_template("checklist.html")


@app.get("/questionnaire")
def questionnaire():
    # If you want to actually render Markdown, handle it in the template.
    return render_template("questionnaire.md")


# ---- PDG ----
@app.get("/pdg")
def pdg_form():
    # Use the actual form template that exists in the repo
    return render_template("pdg_form.html")


@app.post("/pdg/submit")
def pdg_submit():
    # Collect form payload
    form = request.form
    data = {k: v for k, v in form.items()}
    data["__submitted_at__"] = _now_str()

    # Render PDG markdown and HTML preview
    md = render_template("pdg.md.j2", **data)
    (DELIV_DIR / "PDG.md").write_text(md, encoding="utf-8")

    html = render_template("pdg_results.html", **data, rendered_md=md)
    return html


# ---- SOW / HLD / LLD / As-Built ----
@app.get("/sow")
def sow_form():
    return render_template("sow.html")


@app.post("/sow/submit")
def sow_submit():
    form = request.form
    data = {k: v for k, v in form.items()}
    data["__submitted_at__"] = _now_str()

    md = render_template("sow.md.j2", **data)
    (DELIV_DIR / "SOW.md").write_text(md, encoding="utf-8")
    return render_template("presales_submitted.html", what="SOW")


@app.get("/hld")
def hld_form():
    return render_template("hld.html")


@app.post("/hld/submit")
def hld_submit():
    form = request.form
    data = {k: v for k, v in form.items()}
    data["__submitted_at__"] = _now_str()

    md = render_template("hld.md.j2", **data)
    (DELIV_DIR / "HLD.md").write_text(md, encoding="utf-8")
    return render_template("presales_submitted.html", what="HLD")


@app.get("/lld")
def lld_form():
    return render_template("lld.html")


@app.post("/lld/submit")
def lld_submit():
    form = request.form
    data = {k: v for k, v in form.items()}
    data["__submitted_at__"] = _now_str()

    md = render_template("lld.md.j2", **data)
    (DELIV_DIR / "LLD.md").write_text(md, encoding="utf-8")
    return render_template("presales_submitted.html", what="LLD")


@app.get("/asbuilt")
def asbuilt_form():
    return render_template("asbuilt.html")


@app.post("/asbuilt/submit")
def asbuilt_submit():
    form = request.form
    data = {k: v for k, v in form.items()}
    data["__submitted_at__"] = _now_str()

    md = render_template("asbuilt.md.j2", **data)
    (DELIV_DIR / "AsBuilt.md").write_text(md, encoding="utf-8")
    return render_template("presales_submitted.html", what="As-Built")


# ---- Downloads ----
@app.get("/download/md/<name>")
def download_md(name: str):
    path = (DELIV_DIR / name).resolve()
    if DELIV_DIR not in path.parents and path != DELIV_DIR:
        flash("Invalid path.", "error")
        return redirect(url_for("history"))
    if not path.exists():
        flash("File not found.", "error")
        return redirect(url_for("history"))
    return send_file(path, as_attachment=True, download_name=name)


@app.get("/download/docx/<name>")
def download_docx(name: str):
    path = (DOCX_DIR / name).resolve()
    if DOCX_DIR not in path.parents and path != DOCX_DIR:
        flash("Invalid path.", "error")
        return redirect(url_for("history"))
    if not path.exists():
        flash("File not found.", "error")
        return redirect(url_for("history"))
    return send_file(path, as_attachment=True, download_name=name)


# ---- Exports ----
@app.get("/exports")
def exports():
    # list downloadable exports zips
    zips = sorted(EXPORTS_DIR.glob("*.zip"))
    return render_template("exports.html", zips=[f.name for f in zips])


@app.post("/exports/create")
def exports_create():
    """Create a ZIP bundle of the current deliverables & docx outputs."""
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_name = f"deliverables-{ts}.zip"
    out_zip = EXPORTS_DIR / zip_name
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DELIV_DIR.glob("*.md")):
            z.write(p, f"deliverables/{p.name}")
        for p in sorted(DOCX_DIR.glob("*.docx")):
            z.write(p, f"docx/{p.name}")

    flash(f"Created export {zip_name}", "success")
    return redirect(url_for("exports"))


@app.post("/exports/push")
def exports_push():
    """Push latest PDG/LLD/HLD/SOW/AsBuilt markdown to GitHub (if configured)."""
    owner_repo = DEFAULT_REPO
    branch = DEFAULT_BRANCH

    if not (GITHUB_TOKEN and owner_repo):
        flash("GitHub push not configured.", "error")
        return redirect(url_for("history"))

    pushed = []
    for name in ("PDG.md", "LLD.md", "HLD.md", "SOW.md", "AsBuilt.md"):
        p = DELIV_DIR / name
        if p.exists():
            ok = push_export_to_github(owner_repo, branch, f"deliverables/{name}", p.read_bytes(), f"Export {name}")
            if ok:
                pushed.append(name)

    if pushed:
        flash(f"Pushed to GitHub: {', '.join(pushed)}", "success")
    else:
        flash("Nothing to push.", "warning")
    return redirect(url_for("history"))


# ---- Simple Presales (app-level) ----
@app.get("/presales")
def presales():
    return render_template("presales_form.html", form=request.form)


@app.post("/presales/submit")
def presales_submit():
    data = request.form.to_dict(flat=True)
    data["__submitted_at__"] = _now_str()

    # Basic field massaging
    for key in list(data.keys()):
        if key.endswith("_bool"):
            data[key] = _coerce_bool(data[key])

    # Render a simple markdown snapshot
    md = render_template("presales_export.md", **data)
    (DELIV_DIR / "intake.md").write_text(md, encoding="utf-8")
    return render_template("presales_submitted.html")


# ---- Field manager ----
@app.get("/fields")
def manage_fields():
    return render_template("manage_fields.html")


# ---------------- Error Handlers ----------------
@app.errorhandler(404)
def not_found(_e):
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Not Found</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;padding:2rem">'
        "<h1>404 — Not Found</h1>"
        f'<p><a href="{url_for("index")}">Go to Home</a></p>'
        "</body></html>"
    ), 404


@app.errorhandler(500)
def internal_error(_e):
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Server Error</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;padding:2rem">'
        "<h1>500 — Internal Server Error</h1>"
        f'<p><a href="{url_for("index")}">Go to Home</a></p>'
        "</body></html>"
    ), 500


# ---------------- Register Blueprints ----------------
try:
    from presales import presales_bp
    app.register_blueprint(presales_bp)
except Exception:
    # Blueprint is optional; ignore if package not present
    pass


# ---------------- Main ----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "1") == "1")
