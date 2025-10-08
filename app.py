# app.py
from __future__ import annotations

import base64
import io
import json
import math
import os
import time
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

import requests

# Optional Word support (requires python-docx in requirements.txt)
try:
    from docx import Document  # type: ignore
except Exception:
    Document = None

# --------------------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ---------------- GitHub persistence configuration ----------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # "owner/repo"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_PATH = os.getenv("GITHUB_PATH", "data/entries.jsonl")  # path within the repo (no leading slash)
GITHUB_API_ROOT = os.getenv("GITHUB_API_ROOT", "https://api.github.com")

if not (GITHUB_TOKEN and GITHUB_REPO):
    app.logger.warning(
        "GitHub persistence not fully configured. Set GITHUB_TOKEN and GITHUB_REPO."
    )

# Small cache to reduce API calls
_gh_cache: Dict[str, Any] = {"sha": None, "content_text": None, "fetched_ts": 0.0}


def _gh_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "wwt-markdown/1.0",
    }


def _gh_contents_url() -> str:
    p = GITHUB_PATH.lstrip("/")
    return f"{GITHUB_API_ROOT}/repos/{GITHUB_REPO}/contents/{p}"


def gh_check_repo_branch() -> Dict[str, Any]:
    """Quick diagnostics for repo access and branch existence."""
    info: Dict[str, Any] = {
        "repo_ok": False,
        "branch_ok": False,
        "path_leading_slash": GITHUB_PATH.startswith("/"),
        "repo": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
        "path": GITHUB_PATH,
        "token_set": bool(GITHUB_TOKEN),
    }
    try:
        r = requests.get(f"{GITHUB_API_ROOT}/repos/{GITHUB_REPO}", headers=_gh_headers(), timeout=10)
        info["repo_status"] = r.status_code
        info["repo_ok"] = r.status_code == 200
        if info["repo_ok"]:
            rb = requests.get(
                f"{GITHUB_API_ROOT}/repos/{GITHUB_REPO}/branches/{GITHUB_BRANCH}",
                headers=_gh_headers(),
                timeout=10,
            )
            info["branch_status"] = rb.status_code
            info["branch_ok"] = rb.status_code == 200
    except Exception as e:
        info["exception"] = repr(e)
    return info


def gh_read_entries_file(force: bool = False) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (content_text, sha). If file doesn't exist yet, returns ("", None).
    On error, returns (None, None).
    """
    now = time.time()
    if not force and _gh_cache["content_text"] is not None and now - _gh_cache["fetched_ts"] < 10:
        return _gh_cache["content_text"], _gh_cache["sha"]

    params = {"ref": GITHUB_BRANCH}
    try:
        r = requests.get(_gh_contents_url(), headers=_gh_headers(), params=params, timeout=15)
        if r.status_code == 404:
            _gh_cache.update({"content_text": "", "sha": None, "fetched_ts": now})
            return "", None
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict) or "content" not in data:
            return None, None
        content_b64 = data.get("content", "")
        content_decoded = base64.b64decode(content_b64.encode()).decode("utf-8", errors="replace")
        sha = data.get("sha")
        _gh_cache.update({"content_text": content_decoded, "sha": sha, "fetched_ts": now})
        return content_decoded, sha
    except Exception as e:
        app.logger.error(f"GitHub read error: {e}")
        return None, None


def gh_write_entries_file(new_text: str, sha: Optional[str]) -> bool:
    """
    Writes the given text to the repo path. If sha is None, creates the file.
    """
    content_b64 = base64.b64encode(new_text.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Update {GITHUB_PATH} via app at {datetime.utcnow().isoformat()}Z",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(_gh_contents_url(), headers=_gh_headers(), json=payload, timeout=20)
        if r.status_code in (200, 201):
            data = r.json()
            new_sha = data.get("content", {}).get("sha")
            _gh_cache.update({"content_text": new_text, "sha": new_sha, "fetched_ts": time.time()})
            return True
        else:
            app.logger.error(f"GitHub write error ({r.status_code}): {r.text}")
            return False
    except Exception as e:
        app.logger.error(f"GitHub write exception: {e}")
        return False


def gh_save_entries_list(entries: List[Dict[str, Any]]) -> bool:
    """Overwrite the JSONL file with the provided list (used for edits)."""
    _text, sha = gh_read_entries_file()
    new_text = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries)
    return gh_write_entries_file(new_text, sha)


# --------------------------------------------------------------------------------------
# Persistence helpers
# --------------------------------------------------------------------------------------
def _now_utc_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _gen_entry_id() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]


def append_entry(payload: Dict[str, Any]) -> str:
    """Append a JSON line to GitHub file and return new entry_id."""
    entry = dict(payload)
    entry_id = _gen_entry_id()
    entry["entry_id"] = entry_id
    entry["submitted_utc"] = entry.get("submitted_utc") or _now_utc_str()

    content_text, sha = gh_read_entries_file()
    if content_text is None:
        content_text = ""
        sha = None

    new_line = json.dumps(entry, ensure_ascii=False)
    new_text = (content_text + "\n" if content_text and not content_text.endswith("\n") else content_text) + new_line + "\n"
    ok = gh_write_entries_file(new_text, sha)
    if not ok:
        raise RuntimeError("Failed to persist entry to GitHub. Check /ghcheck.")
    return entry_id


def read_all_entries() -> List[Dict[str, Any]]:
    content_text, _sha = gh_read_entries_file()
    if content_text is None:
        return []
    out: List[Dict[str, Any]] = []
    for ln in content_text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return sorted(out, key=lambda x: x.get("entry_id", ""), reverse=True)


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    for e in read_all_entries():
        if e.get("entry_id") == entry_id:
            return e
    return None


def replace_entry(entry_id: str, new_obj: Dict[str, Any]) -> bool:
    """Replace an existing entry (by entry_id) with new_obj."""
    entries = read_all_entries()
    for i, e in enumerate(entries):
        if e.get("entry_id") == entry_id:
            if "submitted_utc" not in new_obj:
                new_obj["submitted_utc"] = e.get("submitted_utc")
            new_obj["entry_id"] = entry_id
            new_obj["updated_utc"] = _now_utc_str()
            entries[i] = new_obj
            return gh_save_entries_list(entries)
    return False


# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", storage_dir=f"github:{GITHUB_REPO}:{GITHUB_PATH}")


@app.route("/presales", methods=["GET", "POST"])
def presales():
    """
    GET: render new form
    POST: create new entry OR update existing (if entry_id present)
    """
    if request.method == "GET":
        return render_template("presales_form.html", form={})

    # ----- POST -----
    form = request.form
    editing_entry_id = (form.get("entry_id") or "").strip() or None

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

    # Validate total = 100 (only if any region boxes were checked)
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
        return render_template("presales_form.html", form=prefill), 400

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

    # Server-side calcs
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
        per_vm_writable = delta_gb + vm_ram_gb + per_vm_overhead_gb
        replicas = num_images * base_image_gb
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

    # Build payload
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
            "gpu_required": bool(form.get("gpu_required")),
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
            "remote_access": bool(form.get("remote_access")),
            "mfa_required": bool(form.get("mfa_required")),
            "mfa_solution": form.get("mfa_solution", ""),
            "smartcard": bool(form.get("smartcard")),
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
            "ad_exists": bool(form.get("ad_exists")),
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
            "local_printing": bool(form.get("local_printing")),
            "usb_redirection": bool(form.get("usb_redirection")),
            "training_required": training_required,
            "onboarding_time_value": as_int("onboarding_time_value"),
            "onboarding_time_unit": form.get("onboarding_time_unit", ""),
            "kt_expectations": form.get("kt_expectations", ""),
            "runbook_required": bool(form.get("runbook_required")),
            "adoption_services": bool(form.get("adoption_services")),
            "ha_dr": bool(form.get("ha_dr")),
            "delivery_model": form.get("delivery_model", ""),
            "start_date": form.get("start_date", ""),
            "timeline": form.get("timeline", ""),
            "docs_requested": docs_requested,
            "stakeholders": form.get("stakeholders", ""),
        }
    )

    # Create new or update existing
    try:
        if editing_entry_id:
            ok = replace_entry(editing_entry_id, data)
            if not ok:
                raise RuntimeError("Entry not found or failed to update on GitHub.")
            data["entry_id"] = editing_entry_id
        else:
            entry_id = append_entry(data)
            data["entry_id"] = entry_id
    except RuntimeError as e:
        flash(str(e), "error")
        # repopulate form with posted values
        prefill = form.to_dict(flat=True)
        prefill["profile_mgmt"] = profile_mgmt
        prefill["virtual_apps"] = virtual_apps
        prefill["docs_requested"] = docs_requested
        prefill["training_required"] = training_required
        for key, _label in REGIONS:
            if form.get(f"region_ck_{key}"):
                prefill[f"region_ck_{key}"] = True
                prefill[f"region_pct_{key}"] = form.get(f"region_pct_{key}", "")
        flash("Open /ghcheck if this keeps happening.", "warning")
        return render_template("presales_form.html", form=prefill), 500

    data["history_url"] = url_for("history")
    data["entry_url"] = url_for("submitted", entry_id=data["entry_id"])
    return render_template("presales_submitted.html", data=data)


@app.route("/presales/edit/<entry_id>")
def presales_edit(entry_id: str):
    """Prefill the presales form to edit an existing submission."""
    e = get_entry(entry_id)
    if not e:
        abort(404)
    e = dict(e)
    e["entry_id"] = entry_id
    return render_template("presales_form.html", form=e, editing=True)


@app.route("/submitted/<entry_id>")
def submitted(entry_id: str):
    e = get_entry(entry_id)
    if not e:
        abort(404)
    e = dict(e)
    e["entry_id"] = entry_id
    e["history_url"] = url_for("history")
    e["entry_url"] = url_for("submitted", entry_id=entry_id)
    return render_template("presales_submitted.html", data=e)


@app.route("/history")
def history():
    entries = read_all_entries()
    return render_template(
        "history.html",
        entries=entries,
        storage_dir=f"github:{GITHUB_REPO}",
        entries_path=GITHUB_PATH,
    )


@app.route("/entry/<entry_id>/payload.json")
def entry_payload(entry_id: str):
    e = get_entry(entry_id)
    if not e:
        abort(404)
    mem = io.BytesIO(json.dumps(e, indent=2).encode("utf-8"))
    mem.seek(0)
    fname = f"presales_payload_{entry_id}.json"
    return send_file(mem, mimetype="application/json", as_attachment=True, download_name=fname)


@app.route("/entry/<entry_id>/package")
def entry_package(entry_id: str):
    # Build a DOCX-only package from a stored entry
    if Document is None:
        flash("Word generation is not available on this deployment (python-docx not installed).", "error")
        return redirect(url_for("submitted", entry_id=entry_id))
    e = get_entry(entry_id)
    if not e:
        abort(404)
    mem, dl_name = _build_doc_package(e)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=dl_name)


@app.route("/presales/package", methods=["POST"])
def presales_package():
    """Build a DOCX-only ZIP from the submitted page via hidden JSON payload."""
    if Document is None:
        flash("Word generation is not available on this deployment (python-docx not installed).", "error")
        return redirect(url_for("presales"))

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


@app.route("/predeploy")
def predeploy():
    return render_template("predeploy.html")


# --------------------------------------------------------------------------------------
# Helpers: package builder (DOCX only; no README or JSON)
# --------------------------------------------------------------------------------------
def _build_docx_bytes(title: str, company: str, opp: str, ir: str, opp_url: str, now_str: str) -> bytes:
    if Document is None:
        return b""
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"Company: {company}")
    doc.add_paragraph(f"Opportunity: {opp}")
    doc.add_paragraph(f"IR: {ir}")
    doc.add_paragraph(f"Opportunity URL: {opp_url or '(n/a)'}")
    doc.add_paragraph(f"Generated: {now_str}")
    doc.add_paragraph("")
    doc.add_paragraph("This is a generated scaffold based on the presales discovery submission.")
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.read()


def _build_doc_package(data: Dict[str, Any]) -> tuple[io.BytesIO, str]:
    """Create an in-memory ZIP with DOCX files only (no README, no JSON)."""
    requested = data.get("docs_requested") or []
    if isinstance(requested, str):
        requested = [requested]

    def safe_name(label: str) -> str:
        base = (
            (label or "").replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
        )
        return base.upper() or "DOCUMENT"

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    company = (data.get("company_name") or "Customer").strip() or "Customer"
    opp = data.get("sf_opportunity_name", "")
    ir = data.get("ir_number", "")
    opp_url = data.get("sf_opportunity_url", "")

    # If no labels were selected, create one default doc so the ZIP isn't empty
    if not requested:
        requested = ["Discovery Summary"]

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write DOCX files only
        for label in requested:
            title = (label or "DOCUMENT").upper()
            docx_bytes = _build_docx_bytes(title, company, opp, ir, opp_url, now)
            if docx_bytes:
                zf.writestr(f"docs/{safe_name(label)}.docx", docx_bytes)

        # ROM convenience
        if any((x or "").upper() in ("ROM", "ROM ESTIMATE") for x in requested):
            docx_bytes = _build_docx_bytes("ROM ESTIMATE", company, opp, ir, opp_url, now)
            if docx_bytes:
                zf.writestr("docs/ROM_ESTIMATE.docx", docx_bytes)

    mem.seek(0)
    dl_name = f"WWT_Doc_Package_{company.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return mem, dl_name


# --------------------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------------------
@app.route("/diag")
def diag():
    content_text, sha = gh_read_entries_file(force=True)
    base = gh_check_repo_branch()
    return {
        "github_repo": GITHUB_REPO,
        "github_branch": GITHUB_BRANCH,
        "github_path": GITHUB_PATH,
        "configured": bool(GITHUB_TOKEN and GITHUB_REPO),
        "repo_ok": base.get("repo_ok"),
        "branch_ok": base.get("branch_ok"),
        "path_leading_slash": base.get("path_leading_slash"),
        "exists_entries": content_text is not None,
        "entries_len_bytes": len(content_text.encode("utf-8")) if isinstance(content_text, str) else None,
        "sha": sha,
        "preview_head": content_text[:500] if isinstance(content_text, str) else None,
    }


@app.route("/ghcheck")
def ghcheck():
    """Human-friendly checklist to fix GitHub write issues."""
    info = gh_check_repo_branch()
    hints = []
    if not info.get("token_set"):
        hints.append("Set GITHUB_TOKEN with Contents: Read/Write.")
    if not info.get("repo_ok"):
        hints.append("GITHUB_REPO must be 'owner/repo' and the token must have access.")
    if not info.get("branch_ok"):
        hints.append(f"GITHUB_BRANCH '{GITHUB_BRANCH}' must exist.")
    if info.get("path_leading_slash"):
        hints.append("GITHUB_PATH must not start with '/'. Use a repo-relative path like 'data/entries.jsonl'.")
    return {
        "repo": info.get("repo"),
        "branch": info.get("branch"),
        "path": info.get("path"),
        "token_set": info.get("token_set"),
        "repo_ok": info.get("repo_ok"),
        "branch_ok": info.get("branch_ok"),
        "path_leading_slash": info.get("path_leading_slash"),
        "hints": hints or ["Looks good. Try submitting the form again."],
    }


# --------------------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------------------
@app.route("/healthz")
def healthz():
    return {
        "ok": True,
        "ts": datetime.utcnow().isoformat(),
        "storage": f"github:{GITHUB_REPO}:{GITHUB_PATH}",
        "branch": GITHUB_BRANCH,
        "configured": bool(GITHUB_TOKEN and GITHUB_REPO),
        "docx_available": Document is not None,
    }


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    # For local runs only; Render will use gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
