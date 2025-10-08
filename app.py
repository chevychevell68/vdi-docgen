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

# Optional Word support (pip install python-docx)
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
    content_text, sha = gh_read_entries_file()
    if content_text is None:
        # treat as create
        sha = None
    new_text = ""
    for e in entries:
        new_text += json.dumps(e, ensure_ascii=False) + "\n"
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
    replaced = False
    for i, e in enumerate(entries):
        if e.get("entry_id") == entry_id:
            # preserve original submitted_utc unless new_obj overrides
            if "submitted_utc" not in new_obj:
                new_obj["submitted_utc"] = e.get("submitted_utc")
            new_obj["entry_id"] = entry_id
            new_obj["updated_utc"] = _now_utc_str()
            entries[i] = new_obj
            replaced = True
            break
    if not replaced:
        return False
    return gh_save_entries_list(entries)


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
        "ir_number": form.get("i_
{% extends "base.html" %}
{% block title %}Pre-Deployment Guide{% endblock %}
{% block content %}
  <h1>Pre-Deployment Guide</h1>
  <p class="text-muted">Placeholder page. Add your checklist/template when ready.</p>
  <div class="btn-group">
    <a class="btn btn-outline-primary" href="{{ url_for('index') }}">Home</a>
    <a class="btn btn-primary" href="{{ url_for('presales') }}">Go to Presales Form</a>
  </div>
{% endblock %}
