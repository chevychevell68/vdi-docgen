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

# ---------- Inject safe helpers for Jinja templates ----------
@app.context_processor
def inject_helpers():
    """
    Provides `has_endpoint(name)` in templates, so you can do:
        {% if has_endpoint('history') %} ... {% endif %}
    """
    def has_endpoint(name: str) -> bool:
        try:
            return name in current_app.view_functions
        except Exception:
            return False
    return dict(has_endpoint=has_endpoint)

# Also inject current_app so legacy templates referencing it won't crash
@app.context_processor
def inject_current_app():
    return dict(current_app=current_app)

# --------- GitHub settings (set these in Render env) ----------
GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "").strip()
REPO_OWNER    = os.getenv("REPO_OWNER", "").strip()
REPO_NAME     = os.getenv("REPO_NAME", "").strip()
REPO_BRANCH   = os.getenv("REPO_BRANCH", "main").strip()

# -------------------- Helpers --------------------

def github_upsert_file(repo_owner: str, repo_name: str, branch: str, path: str, content_bytes: bytes, commit_msg: str) -> bool:
    """Create or update a file via GitHub REST API."""
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
            return 200 <= resp.status < 300
    except HTTPError as e:
        try:
            err_txt = e.read().decode("utf-8", errors="ignore")
        except Exception:
            err_txt = ""
        print("GitHub HTTPError:", e.code, err_txt)
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
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"session-{timestamp}.json"
    rel_dir = "presales_sessions"
    rel_path = f"{rel_dir}/{filename}"
    content = json.dumps(payload, indent=2).encode("utf-8")
    commit_msg = f"Presales submission {filename}"

    if GITHUB_TOKEN and REPO_OWNER and REPO_NAME:
        ok = github_upsert_file(REPO_OWNER, REPO_NAME, REPO_BRANCH, rel_path, content, commit_msg)
        if ok:
            return f"Saved to GitHub: {REPO_OWNER}/{REPO_NAME}@{REPO_BRANCH}/{rel_path}"

    local_path = Path("./data") / rel_path
    ok = save_locally(local_path, content)
    if ok:
        return f"Saved locally at: {local_path}"
    return "Failed to persist (GitHub not configured and local write failed)."

def _as_float(v, dflt):
    try:
        if v is None or v == "":
            return float(dflt)
        return float(v)
    except Exception:
        return float(dflt)

def compute_vsan_capacity(form_dict):
    """
    Total GB for Instant Clones on vSAN (server-side, mirrors client calc).
    Returns int(GB) or None if not applicable.
    """
    if (form_dict.get("storage_type") or "") != "vSAN":
        return None

    N           = _as_float(form_dict.get("concurrent_users"), 0)
    images      = _as_float(form_dict.get("num_images"), 1)
    vmMem       = _as_float(form_dict.get("vm_ram_gb"), 8)
    baseImg     = _as_float(form_dict.get("base_image_gb"), 40)
    factor      = _as_float(form_dict.get("vsan_policy_factor"), 2.0)
    delta       = _as_float(form_dict.get("delta_gb"), 6)
    overhead    = _as_float(form_dict.get("per_vm_overhead_gb"), 1)
    growth      = _as_float(form_dict.get("growth_factor"), 1.10)

    per_vm_writable = delta + vmMem + overhead
    replicas        = images * baseImg
    raw             = (N * per_vm_writable) + replicas
    total           = raw * factor * growth
    return int(math.ceil(total))

def compute_density(form_dict):
    """
    Users per host; min of CPU, RAM, and optional GPU session cap.
    Returns int or None if inputs missing.
    """
    cores    = _as_float(form_dict.get("host_cpu_cores"), 0)
    hostMem  = _as_float(form_dict.get("host_ram_gb"), 0)
    vmvCPU   = _as_float(form_dict.get("vm_vcpu"), 2)
    vmMem    = _as_float(form_dict.get("vm_ram_gb"), 8)
    ratio    = _as_float(form_dict.get("vcpu_to_pcpu"), 4)
    headroom = _as_float(form_dict.get("mem_headroom_pct"), 0.20)
    esxiOH   = _as_float(form_dict.get("esxi_overhead_gb"), 8)
    gpuCap   = _as_float(form_dict.get("gpu_sessions_cap"), 0)

    try:
        cpu_cap = int(math.floor((cores * ratio) / vmvCPU))
        usable  = (hostMem * (1 - headroom)) - esxiOH
        mem_cap = int(math.floor(usable / vmMem))
        d       = min(cpu_cap, mem_cap)
        if gpuCap > 0:
            d = min(d, int(gpuCap))
        return max(0, d)
    except Exception:
        return None

def render_doc_template(name: str, context: dict) -> str:
    """
    Render templates/docs/<name>.md.j2 with Jinja if present,
    otherwise fallback to a short Markdown stub.
    """
    try:
        return render_template(f"docs/{name}.md.j2", data=context)
    except Exception:
        pass

    c = context
    if name == "sow":
        return f"""# Statement of Work (SOW)
**Customer:** {c.get('company_name','')}
**Primary Contact:** {c.get('customer_name','')}
**Deployment Type:** {c.get('deployment_type','')}
**Scope Summary:** {c.get('main_use_cases','')}

## Objectives
- Stand up VMware Horizon environment for ~{c.get('concurrent_users','')} concurrent users
- Regions: {', '.join([f"{k}:{v}%" for k,v in (c.get('location_mix') or {}).items()])}

## Assumptions
- Platform: {c.get('platform','')} | Storage: {c.get('storage_type','')}
- GPU required: {c.get('gpu_required','')}
- Profile mgmt: {', '.join(c.get('profile_mgmt',[])) or '—'}
- Virtual apps: {', '.join(c.get('virtual_apps',[])) or '—'}

## Deliverables
- HLD, LLD, Runbook, PDG, LOE/WBS, ROM, ATP

## Out of Scope
- TBD

## Schedule
- Target start: {c.get('start_date','')}
- Milestones / deadlines: {c.get('timeline','')}
"""
    if name == "hld":
        return f"""# High-Level Design (HLD)
**Customer:** {c.get('company_name','')}
**Deployment Type:** {c.get('deployment_type','')}

## User Requirements
- Total users: {c.get('total_users','—')} | Concurrent: {c.get('concurrent_users','—')}
- Use cases:
{''.join([f"- {u['label']}: {u['text']}\n" for u in c.get('use_cases_list',[])]) or '- —'}

## Logical Architecture
- Platform: {c.get('platform','')}
- vCPU:pCPU: 1:{c.get('vcpu_to_pcpu','4')} | VM size: {c.get('vm_vcpu','')} vCPU / {c.get('vm_ram_gb','')} GB
- Storage: {c.get('storage_type','')} {'(vSAN IC GB ~ ' + str(c.get('vsan_total_gb')) + ')' if c.get('vsan_total_gb') else ''}

## Access & Identity
- Remote access: {c.get('remote_access','')}
- MFA: {c.get('mfa_required','')} {('('+c.get('mfa_solution','')+')') if c.get('mfa_required')=='Yes' else ''}

## Endpoints
- Types: {c.get('endpoint_types','')}
"""
    if name == "loe_wbs":
        return f"""# LOE / WBS
**Customer:** {c.get('company_name','')}

> Placeholder. Replace with your standard task list and hour ranges by phase.

## Phases & Tasks
- Discovery & Planning
- Build & Config
- Image & Apps
- Pilot & Validation
- Knowledge Transfer & Handover
"""
    if name == "rom":
        return f"""# Rough Order of Magnitude (ROM)
**Customer:** {c.get('company_name','')}

> Placeholder. Tie to LOE/WBS once finalized.

## Assumptions
- Concurrent users: {c.get('concurrent_users','')}
- Users per host (est.): {c.get('per_host_density','—')}

## ROM Summary
- TBD
"""
    return f"# {name.upper()}\n\n(Empty template)\n"

# -------------------- Routes --------------------

@app.route("/")
def index():
    # Simple landing menu so we don't accidentally show legacy index.html
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>VDI Tools</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">'
        '</head><body class="p-4" style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial">'
        '<div class="container" style="max-width:920px">'
        '<h1 class="mb-3">VDI Discovery & Docs</h1>'
        '<p class="text-muted">Choose a workflow:</p>'
        '<div class="list-group">'
        f'<a class="list-group-item list-group-item-action" href="{url_for("presales")}">Horizon Presales Discovery</a>'
        f'<a class="list-group-item list-group-item-action" href="{url_for("pdg")}">Project Definition Guide (PDG)</a>'
        f'<a class="list-group-item list-group-item-action" href="{url_for("predeploy")}">Pre-deploy</a>'
        '</div>'
        '</div></body></html>'
    )

@app.route("/presales", methods=["GET", "POST"])
def presales():
    if request.method == "POST":
        data = request.form.to_dict(flat=True)

        # helper to accept both name and name[] from template
        def mgetlist(name: str):
            return request.form.getlist(name) or request.form.getlist(f"{name}[]")

        # Multi-selects / checkboxes
        data["docs_requested"]     = mgetlist("docs_requested")
        data["training_required"]  = mgetlist("training_required")
        data["profile_mgmt"]       = mgetlist("profile_mgmt")
        data["virtual_apps"]       = mgetlist("virtual_apps")

        # Use cases (main + dynamic secondary fields)
        use_cases = []
        main_uc = (data.get("main_use_cases") or "").strip()
        if main_uc:
            use_cases.append({"label": "Main", "text": main_uc})
        for k, v in request.form.items():
            if k.startswith("secondary_use_case_"):
                txt = (v or "").strip()
                if txt:
                    try:
                        n = int(k.rsplit("_", 1)[-1])
                    except ValueError:
                        n = None
                    label = f"Secondary {n}" if n else "Secondary"
                    use_cases.append({"label": label, "text": txt})
        data["use_cases_list"] = use_cases

        # Region mix: build structured map + validate 100%
        REGIONS = [
            ("US","Continental US"),
            ("US_HI","US – HI"),
            ("US_AK","US – AK"),
            ("CAN","Canada"),
            ("LATAM","LATAM"),
            ("EMEA","EMEA"),
            ("APAC","APAC"),
            ("INDIA","India"),
            ("ANZ","ANZ"),
            ("OTHER","Other"),
        ]

        location_mix = {}
        total_pct = 0
        for key, _ in REGIONS:
            if request.form.get(f"region_ck_{key}"):
                pct_raw = (request.form.get(f"region_pct_{key}", "") or "").strip()
                if pct_raw:
                    try:
                        pct = int(round(float(pct_raw)))
                    except ValueError:
                        pct = 0
                    if pct > 0:
                        location_mix[key] = pct
                        total_pct += pct
        if total_pct != 100 and any(request.form.get(f"region_ck_{k}") for k, _ in REGIONS):
            flash(f"Regional mix must total 100% (currently {total_pct}%).", "error")
            return render_template("presales_form.html", form=data)
        data["location_mix"] = location_mix

        # Required fields (minimal set for early version)
        required = ["company_name","customer_name","concurrent_users","host_cpu_cores","host_ram_gb","vm_vcpu","vm_ram_gb"]
        missing = [r for r in required if not (data.get(r) or "").strip()]
        if missing:
            flash(f"Missing required fields: {', '.join(missing)}", "error")
            return render_template("presales_form.html", form=data)

        # Server-side calcs for the summary page
        vsan_total_gb = compute_vsan_capacity(data)
        per_host_density = compute_density(data)
        if vsan_total_gb is not None:
            data["vsan_total_gb"] = vsan_total_gb
        if per_host_density is not None:
            data["per_host_density"] = per_host_density

        # Persist payload
        payload = {"submitted_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", **data}
        where = persist_submission(payload)
        payload["persist_result"] = where

        # Render a results page
        return render_template("presales_submitted.html", data=payload)

    # GET
    return render_template("presales_form.html", form={})

@app.route("/predeploy", methods=["GET"])
def predeploy():
    try:
        return render_template("predeploy.html")
    except Exception:
        return redirect(url_for("presales"))

@app.route("/pdg", methods=["GET"])
def pdg():
    try:
        return render_template("pdg.html")
    except Exception:
        return (
            '<!doctype html><html><head><meta charset="utf-8"><title>PDG</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">'
            '</head><body class="p-4" style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial">'
            '<div class="container" style="max-width:920px">'
            '<h1 class="mb-3">Project Definition Guide (PDG)</h1>'
            '<p class="mb-3">This is a placeholder. Wire this route to your PDG generator/export.</p>'
            f'<a class="btn btn-primary" href="{url_for("presales")}">Open Presales Form</a>'
            '</div></body></html>'
        )

@app.route("/presales/package", methods=["POST"])
def presales_package():
    """
    Create a ZIP containing SOW.md, HLD.md, LOE-WBS.md, ROM.md from the
    submission posted by the results page. If you add Jinja doc templates
    under templates/docs/*.md.j2 they'll be used automatically.
    """
    raw = request.form.get("payload")
    if not raw:
        return "Missing payload", 400
    try:
        data = json.loads(raw)
    except Exception:
        return "Invalid payload", 400

    files = {
        "SOW.md":      render_doc_template("sow", data),
        "HLD.md":      render_doc_template("hld", data),
        "LOE-WBS.md":  render_doc_template("loe_wbs", data),
        "ROM.md":      render_doc_template("rom", data),
    }

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(fname, content)
    mem.seek(0)

    company = (data.get("company_name") or "Customer").replace(" ", "_")
    ts = (data.get("submitted_utc") or "").replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
    zipname = f"{company}_VDI_Doc_Package_{ts or 'now'}.zip"

    return send_file(mem, as_attachment=True, download_name=zipname, mimetype="application/zip")

# ---------------- Error handlers ----------------

@app.errorhandler(404)
def not_found(e):
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Not Found</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;padding:2rem">'
        "<h1>404 — Not Found</h1>"
        f'<p><a href="{url_for("index")}">Go to Home</a></p>'
        "</body></html>"
    ), 404

@app.errorhandler(500)
def server_error(e):
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Server Error</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        '<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;padding:2rem">'
        "<h1>500 — Internal Server Error</h1>"
        f'<p><a href="{url_for("index")}">Go to Home</a></p>'
        "</body></html>"
    ), 500

# ---------------- Main ----------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "1") == "1")
