import os
import io
import time
import base64
import zipfile
from typing import Dict, Any, List

import requests
import yaml
from flask import Flask, render_template, request, send_file, abort, redirect, url_for
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ---------------------------
# Flask app & configuration
# ---------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# GitHub settings (provide via env on your host)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_MAIN = os.getenv("GITHUB_MAIN", "main")
GH_API = "https://api.github.com"

# List of document templates -> output filenames (must exist in templates/docs/)
DOC_TEMPLATES = [
    ("sow.md.j2", "SOW.md"),
    ("loe.md.j2", "LOE.md"),
    ("wbs.md.j2", "WBS.md"),
    ("hld.md.j2", "HLD.md"),
    ("lld.md.j2", "LLD.md"),
    ("atp.md.j2", "ATP.md"),
    ("asbuilt.md.j2", "AsBuilt.md"),
]

# ---------------------------
# Utilities
# ---------------------------

def jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader("templates/docs"),
        undefined=StrictUndefined,   # fail if a template references a missing key
        trim_blocks=True,
        lstrip_blocks=True,
    )

def render_markdown(data: Dict[str, Any]) -> Dict[str, str]:
    """Render all Markdown docs from Jinja templates."""
    env = jinja_env()
    rendered: Dict[str, str] = {}
    for tpl, outname in DOC_TEMPLATES:
        tmpl = env.get_template(tpl)
        rendered[outname] = tmpl.render(**data)
    return rendered

def gh_headers() -> Dict[str, str]:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not set")
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

def gh_main_sha() -> str:
    r = requests.get(
        f"{GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/ref/heads/{GITHUB_MAIN}",
        headers=gh_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["object"]["sha"]

def gh_create_build_branch(slug: str) -> str:
    base_sha = gh_main_sha()
    branch = f"build/{slug}"
    # ensure uniqueness if exists
    r = requests.get(
        f"{GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/ref/heads/{branch}",
        headers=gh_headers(),
        timeout=30,
    )
    if r.status_code == 200:
        branch = f"{branch}-{int(time.time())}"
    r = requests.post(
        f"{GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/refs",
        headers=gh_headers(),
        json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        timeout=30,
    )
    r.raise_for_status()
    return branch

def gh_put_file(branch: str, path: str, content_bytes: bytes, message: str) -> None:
    url = f"{GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "branch": branch,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
    }
    r = requests.put(url, headers=gh_headers(), json=payload, timeout=60)
    r.raise_for_status()

def to_bool(name: str) -> bool:
    return request.form.get(name, "no").lower() in ("yes", "true", "on", "1")

def to_int(name: str, default: int = 0) -> int:
    raw = request.form.get(name, "")
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default

def to_list(name: str) -> List[str]:
    raw = request.form.get(name, "")
    return [t.strip() for t in raw.split(",") if t.strip()]

def val(name: str, default: str = "") -> str:
    return request.form.get(name, default).strip()

# ---------------------------
# Routes
# ---------------------------

@app.get("/")
def home():
    return render_template("home.html")

# ---------- Presales (full scoping questions) ----------

@app.get("/presales")
def presales_get():
    return render_template("forms/presales.html")

@app.post("/presales")
def presales_post():
    slug = val("client_slug") or val("project_name").lower().replace(" ", "-") or "client"

    data = {
        "project": {
            "name": val("project_name"),
            "client_slug": slug,
        },
        "platform": {
            "deployment_model": val("deployment_model"),
            "horizon_license": val("horizon_license"),
            "workspace_one_access": to_bool("workspace_one_access"),
            "virtual_apps_included": to_bool("virtual_apps_included"),
            "profile_mgmt_included": to_bool("profile_mgmt_included"),
            "app_packaging_by_wwt": to_bool("app_packaging_by_wwt"),
        },
        "infra": {
            "hosts": {
                "count": to_int("hosts_count"),
                "type_config": val("hosts_type_config"),
            },
            "storage": {
                "type": val("storage_type"),
                "size_tb": to_int("storage_size_tb"),
                "vendor": val("storage_vendor"),
                "model": val("storage_model"),
            },
            "general_compute_cluster_exists": to_bool("general_compute_cluster_exists"),
        },
        "core": {
            "sql_server": val("sql_server"),
            "dns": to_list("dns"),
            "kms": val("kms"),
            "dhcp": val("dhcp"),
        },
        "identity": {
            "ad_existing": to_bool("ad_existing"),
            "domains_count": to_int("domains_count"),
        },
        "access": {
            "load_balancer": val("load_balancer"),
            "remote_access_required": to_bool("remote_access_required"),
        },
        "endpoints": {
            "setup_by_wwt": to_bool("setup_endpoints"),
            "types": to_list("endpoint_types"),
            "thin_client_mgmt_required": to_bool("thin_client_mgmt_required"),
        },
        "profiles_apps": {
            "profile_mgmt_included": to_bool("profile_mgmt_included"),
            "virtual_apps_included": to_bool("virtual_apps_included"),
            "app_packaging_by_wwt": to_bool("app_packaging_by_wwt"),
        },
        "graphics": {
            "gpu_required": to_bool("gpu_required"),
            "gpu_use_case": val("gpu_use_case"),
        },
        "images": {
            "multiple_required": to_bool("multiple_images_required"),
            "source": val("image_source"),
        },
        "security": {
            "mfa_required": to_bool("mfa_required"),
            "mfa_solution_exists": to_bool("mfa_solution_exists"),
            "smartcard_required": to_bool("smartcard_required"),
            "mdm_required": to_bool("mdm_required"),
        },
        "users_sites_usecases": {
            "concurrent_users": to_int("concurrent_users"),
            "total_users": to_int("total_users"),
            "user_locations": to_list("user_locations"),
            "datacenters": to_list("datacenters"),
            "use_cases_count": to_int("use_cases_count"),
            "main_use_cases": to_list("main_use_cases"),
        },
        "ops_enablement": {
            "ogs_staffing": val("ogs_staffing"),
            "training_type": val("training_type"),
            "training_required": to_bool("training_required"),
            "knowledge_transfer": val("knowledge_transfer"),
            "runbook_required": to_bool("runbook_required"),
            "adoption_services_required": to_bool("adoption_services_required"),
        },
        "resilience_io_monitoring": {
            "ha_da_plan": val("ha_da_plan"),
            "local_printing_required": to_bool("local_printing_required"),
            "mass_storage_devices_required": to_bool("mass_storage_devices_required"),
            "monitoring": val("monitoring"),
            "heavy_onboarding_requirements": to_bool("heavy_onboarding_requirements"),
        },
    }

    # Render all Markdown docs from templates
    files = render_markdown(data)

    # If user checked "push", send MD to build/<slug> and return a success page
    if request.form.get("push_to_github") == "on":
        branch = gh_create_build_branch(slug)
        for name, content in files.items():
            rel = f"output/{slug}/{name}"
            gh_put_file(branch, rel, content.encode("utf-8"), f"Add {rel} (presales)")
        gh_put_file(
            branch,
            f"output/{slug}/intake.presales.yaml",
            yaml.safe_dump(data, sort_keys=False).encode("utf-8"),
            f"Add presales intake for {slug}",
        )
        return render_template("pushed.html", branch=branch, slug=slug)

    # Otherwise send a ZIP to download right now
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("intake.presales.yaml", yaml.safe_dump(data, sort_keys=False))
        for name, content in files.items():
            z.writestr(f"output/{slug}/{name}", content)
    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="presales-output.zip")

# ---------- Pre-Deployment (post-sales / PDG essentials) ----------

@app.get("/predeploy")
def predeploy_get():
    return render_template("forms/predeploy.html")

@app.post("/predeploy")
def predeploy_post():
    slug = val("client_slug") or "client"
    data = {
        "project": {"name": val("project_name", slug), "client_slug": slug},
        "core": {
            "dns": to_list("dns"),
            "ntp": to_list("ntp"),
            "domains": to_list("domains"),
        },
        "access": {
            "load_balancer": val("lb_vendor"),
            "uag": {
                "pod1": {
                    "vip_fqdn": val("pod1_uag_vip"),
                    "cert_cn": val("pod1_uag_cert"),
                }
            },
        },
        "security": {
            "mfa_vendor": val("mfa_vendor"),
        },
        "images": {
            "os": to_list("image_os"),
            "count": to_int("image_count", 1),
        },
        "topology": {
            "pods": [
                {
                    "name": "Pod 1",
                    "site": val("pod1_site", "DC1"),
                    "region": val("pod1_region", "Central US"),
                    "vcenter": val("pod1_vcenter"),
                }
            ]
        },
        "security_fw": {
            "internal": val("internal_fw"),
            "external": val("external_fw"),
        },
    }

    files = render_markdown(data)

    if request.form.get("push_to_github") == "on":
        branch = gh_create_build_branch(slug)
        for name, content in files.items():
            rel = f"output/{slug}/{name}"
            gh_put_file(branch, rel, content.encode("utf-8"), f"Add {rel} (predeploy)")
        gh_put_file(
            branch,
            f"output/{slug}/intake.predeploy.yaml",
            yaml.safe_dump(data, sort_keys=False).encode("utf-8"),
            f"Add predeploy intake for {slug}",
        )
        return render_template("pushed.html", branch=branch, slug=slug)

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("intake.predeploy.yaml", yaml.safe_dump(data, sort_keys=False))
        for name, content in files.items():
            z.writestr(f"output/{slug}/{name}", content)
    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="predeploy-output.zip")

# ---------- Download latest DOCX artifact for a slug ----------

@app.get("/docx/<slug>")
def download_docx(slug: str):
    """
    Try to fetch the most recent artifacts for the repo and return the first 'docx-*' ZIP.
    Fallback: show a link to the committed files under output-docx/<slug>/ on main.
    """
    try:
        r = requests.get(
            f"{GH_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/artifacts",
            headers=gh_headers(),
            timeout=30,
        )
        r.raise_for_status()
        for art in r.json().get("artifacts", []):
            if art.get("expired"):
                continue
            name = art.get("name", "")
            if "docx" in name.lower():  # artifact uploaded by your workflow
                dl = requests.get(art["archive_download_url"], headers=gh_headers(), timeout=60)
                dl.raise_for_status()
                return send_file(
                    io.BytesIO(dl.content),
                    mimetype="application/zip",
                    as_attachment=True,
                    download_name=f"{name}.zip",
                )
        # No artifact found—offer direct repo link
        repo_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/{GITHUB_MAIN}/output-docx/{slug}"
        return render_template("no_artifact.html", slug=slug, repo=repo_url)
    except Exception as e:
        return abort(400, f"Could not fetch artifacts: {e}")

# ---------------------------
# Main (for local dev)
# ---------------------------
if __name__ == "__main__":
    # For local testing only; on Render use: gunicorn app:app --bind 0.0.0.0:$PORT
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
