# app.py
from __future__ import annotations

import io
import json
import math
import os
import textwrap
import zipfile
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from flask import (
    Flask,
    render_template,
    render_template_string,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    abort,
)

# --------------------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# Persistent storage dir:
# - Prefer /var/data on Render (persistent disk)
# - Fall back to ./data locally
STORAGE_DIR_CANDIDATES = ["/var/data", "./data"]
for _d in STORAGE_DIR_CANDIDATES:
    try:
        os.makedirs(_d, exist_ok=True)
        STORAGE_DIR = _d
        break
    except Exception:
        continue
else:
    # Last resort: current dir (may be ephemeral)
    STORAGE_DIR = "."

ENTRIES_PATH = os.path.join(STORAGE_DIR, "entries.jsonl")


# --------------------------------------------------------------------------------------
# Utilities: persistence (JSONL append-only)
# --------------------------------------------------------------------------------------
def _now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def _gen_entry_id() -> str:
    # time-ordered-ish id with UUID suffix
    return datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]

def _safe_read_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()

def _write_line(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def append_entry(payload: Dict[str, Any]) -> str:
    """Append a submission to entries.jsonl and return an entry_id."""
    entry = dict(payload)  # shallow copy
    entry_id = _gen_entry_id()
    entry["entry_id"] = entry_id
    # Normalize a submitted timestamp field
    entry["submitted_utc"] = entry.get("submitted_utc") or _now_utc_str()
    _write_line(ENTRIES_PATH, json.dumps(entry, ensure_ascii=False))
    return entry_id

def read_all_entries() -> List[Dict[str, Any]]:
    lines = _safe_read_lines(ENTRIES_PATH)
    out: List[Dict[str, Any]] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    # Newest first (sort by entry_id timestamp portion)
    return sorted(out, key=lambda x: x.get("entry_id", ""), reverse=True)

def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    for e in read_all_entries():
        if e.get("entry_id") == entry_id:
            return e
    return None


# --------------------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------------------
@app.route("/")
def index():
    # Simple home even if base.html is missing
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>VDI Tools</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container" style="max-width: 920px;">
    <h1 class="mb-4">VDI Discovery Tools</h1>
    <div class="list-group">
      <a class="list-group-item list-group-item-action" href="{{ url_for('presales') }}">Presales Discovery Form</a>
      <a class="list-group-item list-group-item-action" href="{{ url_for('pdg') }}">Project Definition Guide (PDG)</a>
      <a class="list-group-item list-group-item-action" href="{{ url_for('predeploy') }}">Pre-deploy Checklist</a>
      <a class="list-group-item list-group-item-action" href="{{ url_for('history') }}">History (Past Submissions)</a>
    </div>
    <div class="text-muted mt-4">Home v2.0 — Storage: <code>{{ storage_dir }}</code></div>
  </div>
</body>
</html>
        """,
        storage_dir=STORAGE_DIR,
    )


# --------------------------------------------------------------------------------------
# Presales form (GET/POST)
# --------------------------------------------------------------------------------------
@app.route("/presales", methods=["GET", "POST"])
def presales():
    """
    GET: render form
    POST: validate + compute + show submitted summary + persist entry
    """
    # Try to render your Jinja template if present; otherwise fallback
    def _render_presales_form(form: Dict[str, Any]):
        try:
            return render_template("presales_form.html", form=form)
        except Exception:
            # Minimal fallback form
            return render_template_string(
                """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Presales (Fallback)</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-4">
<div class="container" style="max-width: 920px;">
  <h1>Presales (Fallback)</h1>
  <p class="text-muted">Your <code>presales_form.html</code> template was not found. This is a minimal fallback.</p>
  <form method="post" class="mt-3">
    <div class="mb-3">
      <label class="form-label">Company Name</label>
      <input name="company_name" class="form-control" placeholder="Acme Corp">
    </div>
    <div class="mb-3">
      <label class="form-label">Total Users</label>
      <input name="total_users" class="form-control" type="number" value="100">
    </div>
    <div class="mb-3">
      <label class="form-label">Concurrent Users</label>
      <input name="concurrent_users" class="form-control" type="number" value="60">
    </div>
    <div class="mb-3">
      <label class="form-label">Storage Type</label>
      <select name="storage_type" class="form-select">
        <option value="">--</option>
        <option value="vSAN">vSAN</option>
        <option value="Other">Other</option>
      </select>
    </div>
    <button class="btn btn-primary" type="submit">Submit</button>
  </form>
</div></body></html>
                """
            )

    if request.method == "GET":
        return _render_presales_form(form={})

    # ----- POST -----
    form = request.form

    # Multi-select fields (checkbox groups)
    profile_mgmt = request.form.getlist("profile_mgmt")
    virtual_apps = request.form.getlist("virtual_apps")
    docs_requested = request.form.getlist("docs_requested")
    training_required = request.form.getlist("training_required")

    REGIONS: List[Tuple[str, str]] = [
        ("US", "Continental US"),
        ("US_HI", "US – HI"),
        ("US_AK", "US – AK"),
        ("CAN", "Canada"),
        ("LATAM", "LATAM"),
        ("EMEA", "EMEA"),
        ("APAC", "APAC"),
        ("INDIA", "India"),
        ("ANZ", "ANZ"),
        ("OTHER", "Other"),
    ]

    # Build regional mix safely
    location_mix: Dict[str, int] = {}
    for key, _label in REGIONS:
        if form.get(f"region_ck_{key}"):
            raw = (form.get(f"region_pct_{key}") or "").strip()
            if raw:
                try:
                    pct = int(raw)
                except ValueError:
                    pct = 0
                location_mix[key] = pct

    # Validate total = 100
    if sum(location_mix.values()) != 100 and any(form.get(f"region_ck_{k}") for k, _ in REGIONS):
        flash("Regional mix must total 100%.", "error")
        prefill = form.to_dict(flat=True)
        prefill["profile_mgmt"] = profile_mgmt
        prefill["virtual_apps"] = virtual_apps
        prefill["docs_requested"] = docs_requested
        prefill["training_required"] = training_required
        for key, _label in REGIONS:
            if form.get(f"region_ck_{key}"):
                prefill[f"region_ck_{key}"] = True
                prefill[f"region_pct_{key}"] = form.get(f"region_pct_{key}", "")
        return _render_presales_form(form=prefill), 400

    # Utilities
    def as_int(name: str, default=None):
        v = form.get(name, "").strip()
        if v == "":
            return default
        try:
            return int(v)
        except ValueError:
            return default

    def as_float(name: str, default=None):
        v = form.get(name, "").strip()
        if v == "":
            return default
        try:
            return float(v)
        except ValueError:
            return default

    # Server-side calcs mirroring the JS (so summary/ZIP have numbers even if JS was bypassed)
    concurrent_users = as_int("concurrent_users", 0) or 0
    num_images = as_int("num_images", 1) or 1
    vm_ram_gb = as_float("vm_ram_gb", 8.0) or 8.0
    base_image_gb = as_float("base_image_gb", 40.0) or 40.0
    vsan_policy_factor = as_float("vsan_policy_factor", 2.0) or 2.0
    delta_gb = as_float("delta_gb", 6.0) or 6.0
    per_vm_overhead_gb = as_float("per_vm_overhead_gb", 1.0) or 1.0
    growth_factor = as_float("growth_factor", 1.10) or 1.10

    storage_type = form.get("storage_type", "")
    vsan_total_gb = None
    if storage_type == "vSAN":
        per_vm_writable = delta_gb + vm_ram_gb + per_vm_overhead_gb  # delta + mem + overhead
        replicas = num_images * base_image_gb                        # base image replicas
        raw = (concurrent_users * per_vm_writable) + replicas
        vsan_total_gb = math.ceil(raw * vsan_policy_factor * growth_factor)

    host_cpu_cores = as_int("host_cpu_cores", 0) or 0
    host_ram_gb = as_float("host_ram_gb", 0.0) or 0.0
    vm_vcpu = as_int("vm_vcpu", 2) or 2
    mem_headroom_pct = as_float("mem_headroom_pct", 0.20) or 0.20
    esxi_overhead_gb = as_float("esxi_overhead_gb", 8.0) or 8.0
    vcpu_to_pcpu = as_int("vcpu_to_pcpu", 4) or 4
    gpu_sessions_cap = as_int("gpu_sessions_cap", 0) or 0

    per_host_density = None
    try:
        cpu_cap = (host_cpu_cores * vcpu_to_pcpu) // vm_vcpu if vm_vcpu > 0 else 0
        usable_mem = (host_ram_gb * (1 - mem_headroom_pct)) - esxi_overhead_gb
        mem_cap = int(usable_mem // vm_ram_gb) if vm_ram_gb > 0 else 0
        d = min(cpu_cap, mem_cap)
        if gpu_sessions_cap > 0:
            d = min(d, gpu_sessions_cap)
        per_host_density = max(0, d)
    except Exception:
        per_host_density = None

    # Build payload for summary
    data: Dict[str, Any] = {
        # Customer
        "company_name": form.get("company_name", ""),
        "customer_name": form.get("customer_name", ""),
        "sf_opportunity_name": form.get("sf_opportunity_name", ""),
        "sf_opportunity_url": form.get("sf_opportunity_url", ""),
        "ir_number": form.get("ir_number", ""),
        "voc": form.get("voc", ""),
        "submitted_utc": _now_utc_str(),

        # Existing VDI
        "existing_vdi": form.get("existing_vdi", ""),
        "existing_vdi_pain": form.get("existing_vdi_pain", ""),

        # Users & Scope
        "total_users": as_int("total_users"),
        "concurrent_users": concurrent_users,
        "num_datacenters": as_int("num_datacenters"),
        "datacenters_detail": form.get("datacenters_detail", ""),
        "deployment_type": form.get("deployment_type", ""),
        "location_mix": location_mix,
        "num_personas": as_int("num_personas"),
        "main_use_cases": form.get("main_use_cases", ""),
        "use_cases_list": [],
    }

    # Use-cases list (main + N secondary)
    if data["main_use_cases"]:
        data["use_cases_list"].append({"label": "Main", "text": data["main_use_cases"]})
    n_personas = data["num_personas"] or 0
    for i in range(2, n_personas + 1):
        v = (form.get(f"secondary_use_case_{i}", "") or "").strip()
        if v:
            data["use_cases_list"].append({"label": f"Secondary {i}", "text": v})

    # GPU
    data.update(
        {
            "gpu_required": form.get("gpu_required", ""),
            "gpu_users": as_int("gpu_users"),
            "gpu_vram_per_user": as_float("gpu_vram_per_user"),
            "gpu_use_case": form.get("gpu_use_case", ""),
        }
    )

    # Image & Apps
    data.update(
        {
            "num_images": num_images,
            "gold_image_source": form.get("gold_image_source", ""),
            "profile_mgmt": profile_mgmt,
            "virtual_apps": virtual_apps,
            "required_apps": form.get("required_apps", ""),
            "wwt_app_packaging": form.get("wwt_app_packaging", ""),
        }
    )

    # Access & Identity
    data.update(
        {
            "remote_access": form.get("remote_access", ""),
            "mfa_required": form.get("mfa_required", ""),
            "mfa_solution": form.get("mfa_solution", ""),
            "smartcard": form.get("smartcard", ""),
            "idp_provider": form.get("idp_provider", ""),
        }
    )

    # Endpoints
    data.update(
        {
            "endpoint_provisioning": form.get("endpoint_provisioning", ""),
            "endpoint_types": form.get("endpoint_types", ""),
            "thin_client_mgmt": form.get("thin_client_mgmt", ""),
        }
    )

    # Directory & Core
    data.update(
        {
            "ad_exists": form.get("ad_exists", ""),
            "num_domains": as_int("num_domains"),
            "vd_domain_name": form.get("vd_domain_name", ""),
            "core_domain_name": form.get("core_domain_name", ""),
        }
    )

    # Platform & Infra
    data.update(
        {
            "platform": form.get("platform", ""),
            "general_compute_cluster": form.get("general_compute_cluster", ""),
            "host_cpu_cores": host_cpu_cores,
            "host_ram_gb": host_ram_gb,
            "hosts_count": as_int("hosts_count"),
            "vm_vcpu": vm_vcpu,
            "vm_ram_gb": vm_ram_gb,
            "vcpu_to_pcpu": vcpu_to_pcpu,
            "storage_type": storage_type,
            "storage_vendor_model": form.get("storage_vendor_model", ""),
            "storage_protocol": form.get("storage_protocol", ""),
            "storage_usable_gb": as_int("storage_usable_gb"),
            "base_image_gb": base_image_gb,
            "vsan_policy_factor": vsan_policy_factor,
            "delta_gb": delta_gb,
            "per_vm_overhead_gb": per_vm_overhead_gb,
            "growth_factor": growth_factor,
            "mem_headroom_pct": mem_headroom_pct,
            "esxi_overhead_gb": esxi_overhead_gb,
            "gpu_sessions_cap": gpu_sessions_cap,
            "vsan_total_gb": vsan_total_gb,
            "per_host_density": per_host_density,
            "load_balancer": form.get("load_balancer", ""),
        }
    )

    # Ops & Delivery
    data.update(
        {
            "ogs_staffing": form.get("ogs_staffing", ""),
            "monitoring_stack": form.get("monitoring_stack", ""),
            "local_printing": form.get("local_printing", ""),
            "usb_redirection": form.get("usb_redirection", ""),
            "training_required": training_required,
            "onboarding_time_value": as_int("onboarding_time_value"),
            "onboarding_time_unit": form.get("onboarding_time_unit", ""),
            "kt_expectations": form.get("kt_expectations", ""),
            "runbook_required": form.get("runbook_required", ""),
            "adoption_services": form.get("adoption_services", ""),
            "ha_dr": form.get("ha_dr", ""),
            "delivery_model": form.get("delivery_model", ""),
            "start_date": form.get("start_date", ""),
            "timeline": form.get("timeline", ""),
            "docs_requested": docs_requested,
            "stakeholders": form.get("stakeholders", ""),
        }
    )

    # Persist the entry and annotate with id + history links
    entry_id = append_entry(data)
    data["entry_id"] = entry_id
    data["history_url"] = url_for("history")
    data["entry_url"] = url_for("entry_detail", entry_id=entry_id)

    # Try your real template; else fallback
    try:
        return render_template("presales_submitted.html", data=data)
    except Exception:
        return render_template_string(
            """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Submission Saved</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-4">
<div class="container" style="max-width: 960px;">
  <h1 class="mb-3">Submission Saved</h1>
  <div class="alert alert-success">Saved as Entry ID: <strong>{{ data.entry_id }}</strong></div>
  <p>
    <a class="btn btn-primary" href="{{ url_for('entry_detail', entry_id=data.entry_id) }}">Open Entry</a>
    <a class="btn btn-outline-secondary" href="{{ url_for('history') }}">View History</a>
  </p>
  <hr>
  <h5>Quick Details</h5>
  <pre class="p-3 bg-light border rounded" style="white-space:pre-wrap">{{ data | tojson(indent=2) }}</pre>
</div></body></html>
            """,
            data=data,
        )


# --------------------------------------------------------------------------------------
# ZIP package generation (for current page POST back)
# --------------------------------------------------------------------------------------
@app.route("/presales/package", methods=["POST"])
def presales_package():
    """
    Build a ZIP of requested docs based on a hidden JSON payload posted
    from the submitted page.
    """
    payload = request.form.get("payload", "")
    if not payload:
        flash("Missing payload for package generation.", "error")
        return redirect(url_for("presales"))

    try:
        data = json.loads(payload)
    except Exception:
        flash("Invalid payload for package generation.", "error")
        return redirect(url_for("presales"))

    mem, dl_name = _build_doc_package(data)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=dl_name)


# --------------------------------------------------------------------------------------
# PDG / Pre-deploy placeholders
# --------------------------------------------------------------------------------------
@app.route("/pdg")
def pdg():
    # Minimal page so the link doesn't 404. Replace with your real PDG template anytime.
    return render_template_string(
        """
{% extends "base.html" %}
{% block title %}PDG{% endblock %}
{% block content %}
<h1>Project Definition Guide (PDG)</h1>
<p class="text-muted">Placeholder page. Wire this to your actual PDG flow when ready.</p>
<a class="btn btn-primary" href="{{ url_for('presales') }}">Go to Presales Form</a>
{% endblock %}
        """
    )


@app.route("/predeploy")
def predeploy():
    # Minimal page so the link doesn't 404. Replace with your real pre-deploy template anytime.
    return render_template_string(
        """
{% extends "base.html" %}
{% block title %}Pre-deploy{% endblock %}
{% block content %}
<h1>Pre-deploy Checklist</h1>
<p class="text-muted">Placeholder page. Add your checklist template when ready.</p>
<a class="btn btn-primary" href="{{ url_for('presales') }}">Go to Presales Form</a>
{% endblock %}
        """
    )


# --------------------------------------------------------------------------------------
# History & Entry detail
# --------------------------------------------------------------------------------------
@app.route("/history")
def history():
    entries = read_all_entries()
    return render_template_string(
        """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>History</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-4">
<div class="container" style="max-width: 1100px;">
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h1 class="mb-0">History</h1>
    <a class="btn btn-primary" href="{{ url_for('presales') }}">New Submission</a>
  </div>
  {% if not entries %}
    <div class="alert alert-info">No entries yet.</div>
  {% else %}
    <div class="table-responsive">
    <table class="table table-sm align-middle">
      <thead><tr><th>When (UTC)</th><th>Company</th><th>Opp</th><th>IR</th><th>Actions</th></tr></thead>
      <tbody>
        {% for e in entries %}
          <tr>
            <td><code>{{ e.submitted_utc }}</code></td>
            <td>{{ e.company_name or '—' }}</td>
            <td>{{ e.sf_opportunity_name or '—' }}</td>
            <td>{{ e.ir_number or '—' }}</td>
            <td>
              <a class="btn btn-sm btn-outline-primary" href="{{ url_for('entry_detail', entry_id=e.entry_id) }}">Open</a>
              <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('entry_payload', entry_id=e.entry_id) }}">Payload JSON</a>
              <a class="btn btn-sm btn-outline-success" href="{{ url_for('entry_package', entry_id=e.entry_id) }}">Build Package</a>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
    </div>
  {% endif %}
  <div class="text-muted mt-4">Storage dir: <code>{{ storage_dir }}</code> · File: <code>{{ entries_path }}</code></div>
</div></body></html>
        """,
        entries=entries,
        storage_dir=STORAGE_DIR,
        entries_path=ENTRIES_PATH,
    )


@app.route("/entry/<entry_id>")
def entry_detail(entry_id: str):
    e = get_entry(entry_id)
    if not e:
        abort(404)
    return render_template_string(
        """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Entry {{ e.entry_id }}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-4">
<div class="container" style="max-width: 1100px;">
  <div class="d-flex align-items-center justify-content-between mb-3">
    <h1 class="mb-0">Entry <small class="text-muted">{{ e.entry_id }}</small></h1>
    <div class="btn-group">
      <a class="btn btn-outline-secondary" href="{{ url_for('entry_payload', entry_id=e.entry_id) }}">Download Payload JSON</a>
      <a class="btn btn-success" href="{{ url_for('entry_package', entry_id=e.entry_id) }}">Build Package</a>
      <a class="btn btn-primary" href="{{ url_for('history') }}">Back to History</a>
    </div>
  </div>
  <div class="row">
    <div class="col-lg-6">
      <div class="card mb-3">
        <div class="card-body">
          <h5 class="card-title">Summary</h5>
          <ul class="mb-0">
            <li><strong>Company:</strong> {{ e.company_name or '—' }}</li>
            <li><strong>Opportunity:</strong> {{ e.sf_opportunity_name or '—' }}</li>
            <li><strong>IR:</strong> {{ e.ir_number or '—' }}</li>
            <li><strong>Submitted (UTC):</strong> <code>{{ e.submitted_utc }}</code></li>
            <li><strong>Docs Requested:</strong> {{ (e.docs_requested or []) | join(', ') if e.docs_requested else '—' }}</li>
          </ul>
        </div>
      </div>
    </div>
    <div class="col-lg-6">
      <div class="card mb-3">
        <div class="card-body">
          <h5 class="card-title">Location Mix</h5>
          <pre class="mb-0 bg-light p-2 border rounded" style="white-space:pre-wrap">{{ (e.location_mix or {}) | tojson(indent=2) }}</pre>
        </div>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-body">
      <h5 class="card-title">Full Payload</h5>
      <pre class="mb-0 bg-light p-2 border rounded" style="white-space:pre-wrap">{{ e | tojson(indent=2) }}</pre>
    </div>
  </div>
</div></body></html>
        """,
        e=e,
    )


@app.route("/entry/<entry_id>/payload.json")
def entry_payload(entry_id: str):
    e = get_entry(entry_id)
    if not e:
        abort(404)
    # Stream JSON without writing to disk
    mem = io.BytesIO(json.dumps(e, indent=2).encode("utf-8"))
    mem.seek(0)
    fname = f"presales_payload_{entry_id}.json"
    return send_file(mem, mimetype="application/json", as_attachment=True, download_name=fname)


@app.route("/entry/<entry_id>/package")
def entry_package(entry_id: str):
    e = get_entry(entry_id)
    if not e:
        abort(404)
    mem, dl_name = _build_doc_package(e)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=dl_name)


# --------------------------------------------------------------------------------------
# Shared: package builder
# --------------------------------------------------------------------------------------
def _build_doc_package(data: Dict[str, Any]) -> tuple[io.BytesIO, str]:
    """Create the in-memory ZIP using the current/archived payload."""
    requested = data.get("docs_requested") or []
    if isinstance(requested, str):
        requested = [requested]

    def safe_name(label: str) -> str:
        base = (
            label.replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
        )
        return base.upper()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    company = (data.get("company_name") or "Customer").strip() or "Customer"
    opp = data.get("sf_opportunity_name", "")
    ir = data.get("ir_number", "")
    opp_url = data.get("sf_opportunity_url", "")

    def doc_body(title: str) -> str:
        header = f"{title}\n{'=' * len(title)}\n"
        meta = textwrap.dedent(
            f"""
            Company: {company}
            Opportunity: {opp}
            IR: {ir}
            Opportunity URL: {opp_url or '(n/a)'}
            Generated: {now}

            """
        )
        summary = "This is a generated scaffold based on the presales discovery submission.\n\n"
        return header + meta + summary

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # README
        zf.writestr(
            "README.txt",
            textwrap.dedent(
                f"""\
                Document Package
                =================
                Generated: {now}

                Included documents: {', '.join(requested) if requested else '(none specified)'}
                """
            ),
        )
        # JSON context for downstream tools
        zf.writestr("context/presales_payload.json", json.dumps(data, indent=2))

        # Write each requested doc as a .md scaffold
        for label in requested:
            fname = safe_name(label)
            title = label.upper()
            zf.writestr(f"docs/{fname}.md", doc_body(title))

        # Include a quick ROM text if requested
        if any((x or "").upper() in ("ROM", "ROM ESTIMATE") for x in requested):
            zf.writestr("docs/ROM_ESTIMATE.md", doc_body("ROM ESTIMATE"))

    mem.seek(0)
    dl_name = f"WWT_VDI_Doc_Package_{company.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return mem, dl_name


# --------------------------------------------------------------------------------------
# Health (useful for Render)
# --------------------------------------------------------------------------------------
@app.route("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat(), "storage_dir": STORAGE_DIR, "entries_path": ENTRIES_PATH}


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    # For local runs only; Render will use gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
