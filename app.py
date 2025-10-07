import os
import json
import base64
import datetime as dt
from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for, flash
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# --------- GitHub settings (set in Render) ----------
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "").strip()
REPO_OWNER    = os.getenv("REPO_OWNER", "").strip()
REPO_NAME     = os.getenv("REPO_NAME", "").strip()
REPO_BRANCH   = os.getenv("REPO_BRANCH", "main").strip()

def github_upsert_file(repo_owner: str, repo_name: str, branch: str, path: str, content_bytes: bytes, commit_msg: str) -> bool:
    """
    Create a new file in GitHub via the Contents API.
    If the file exists, this will fail unless you first fetch the SHA and include it.
    We generate unique timestamped filenames, so create is sufficient.
    """
    if not (GITHUB_TOKEN and repo_owner and repo_name and branch and path):
        return False

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"
    body = {
        "message": commit_msg,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch
    }
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, method="PUT", headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28"
    })
    try:
        with urlopen(req) as resp:
            # 201 Created expected
            return 200 <= resp.status < 300
    except HTTPError as e:
        # Surface a friendly error in logs; UI message handled by flash
        print("GitHub HTTPError:", e.code, e.read().decode("utf-8", errors="ignore"))
        return False
    except URLError as e:
        print("GitHub URLError:", e.reason)
        return False

def save_locally(path: Path, content_bytes: bytes) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content_bytes)
        return True
    except Exception as e:
        print("Local save error:", e)
        return False

def persist_submission(payload: dict) -> str:
    """
    Persist payload as JSON to GitHub (preferred) or local disk (fallback).
    Returns a human-readable message about where it went.
    """
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"session-{timestamp}.json"
    rel_dir = "presales_sessions"
    rel_path = f"{rel_dir}/{filename}"

    content = json.dumps(payload, indent=2).encode("utf-8")
    commit_msg = f"Presales submission {filename}"

    # Try GitHub first
    if GITHUB_TOKEN and REPO_OWNER and REPO_NAME:
        ok = github_upsert_file(REPO_OWNER, REPO_NAME, REPO_BRANCH, rel_path, content, commit_msg)
        if ok:
            return f"Saved to GitHub: {REPO_OWNER}/{REPO_NAME}@{REPO_BRANCH}/{rel_path}"

    # Fallback: local (Render disk)
    local_path = Path("./data") / rel_path
    ok = save_locally(local_path, content)
    if ok:
        return f"Saved locally at: {local_path}"
    return "Failed to persist (GitHub not configured and local write failed)."

@app.route("/")
def index():
    # Minimal landing page if you don't have a custom index.html
    try:
        app.jinja_env.get_or_select_template("index.html")
        return render_template("index.html")
    except Exception:
        return (
            '<!doctype html><html><head><meta charset="utf-8"><title>VDI DocGen</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
            '<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;padding:2rem">'
            "<h1>VDI DocGen</h1>"
            '<p><a href="/presales">Open Horizon Presales Discovery form</a></p>'
            "</body></html>"
        )

# -------------- NOTE: route changed to /presales (no /new) --------------
@app.route("/presales", methods=["GET", "POST"])
def presales():
    """
    Architect-led Horizon presales discovery form.
    Renders templates/presales_form.html.
    """
    if request.method == "POST":
        # Flatten + collect multi-selects
        data = request.form.to_dict(flat=True)
        # Build a structured region mix (only checked + >0 values)
REGIONS = [
    ("US", "Continental US"),
    ("CAN", "Canada"),
    ("LATAM", "LATAM"),
    ("EMEA", "EMEA"),
    ("APAC", "APAC"),
    ("INDIA", "India"),
    ("ANZ", "ANZ"),
    ("OTHER", "Other"),
]

location_mix = {}
total_pct = 0
for key, _label in REGIONS:
    checked = request.form.get(f"region_ck_{key}")
    pct_raw = request.form.get(f"region_pct_{key}", "").strip()
    if checked and pct_raw:
        try:
            pct = int(round(float(pct_raw)))
        except ValueError:
            pct = 0
        if pct > 0:
            location_mix[key] = pct
            total_pct += pct

# Server-side enforcement: must equal 100%
if total_pct != 100:
    flash(f"Regional mix must total 100% (currently {total_pct}%).", "error")
    return render_template("presales_form.html", form=data)

# Put the structured mix into the payload
data["location_mix"] = location_mix

        data["docs_requested"]    = request.form.getlist("docs_requested")
        data["training_required"] = request.form.getlist("training_required")

        # Basic validation
        required = [
            "company_name", "customer_name",
            "concurrent_users",
            "host_cpu_cores", "host_ram_gb",
            "vm_vcpu", "vm_ram_gb",
        ]
        missing = [r for r in required if not (data.get(r) or "").strip()]
        if missing:
            flash(f"Missing required fields: {', '.join(missing)}", "error")
            return render_template("presales_form.html", form=data)

        # Add metadata (UTC timestamp) to payload
        payload = {
            "submitted_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            **data
        }

        where = persist_submission(payload)
        if where.startswith("Failed"):
            flash(where, "error")
        else:
            flash(f"Presales discovery saved. {where}", "success")

        return redirect(url_for("presales"))

    # GET
    return render_template("presales_form.html")

@app.errorhandler(404)
def not_found(e):
    try:
        return render_template("404.html"), 404
    except Exception:
        return "Not Found", 404

@app.errorhandler(500)
def server_error(e):
    try:
        return render_template("500.html"), 500
    except Exception:
        return "Internal Server Error", 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "1") == "1")
