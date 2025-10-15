# pandoc_gen.py — Generate DOCX via Pandoc from Jinja2 Markdown templates (no app.py changes required)
from __future__ import annotations
import subprocess, shlex, os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, DictLoader, select_autoescape

# Default inline templates (used only if files not found on disk)
INLINE_TEMPLATES = {
    "sow.md.j2": """# Statement of Work
**Project:** {{ project_name|default("Project") }}
**Customer:** {{ customer_name|default("Customer") }}

## Introduction
This Statement of Work describes services to design and deploy an Omnissa Horizon environment. Work is executed under the EPDIO framework (Engage, Plan, Design, Implement, Operate).

## Scope
- Target users: {{ total_users or user_count or "(from presales)" }}
- Regions: {{ regions or "(from presales)" }}
- GPU: {{ gpu_required or "No" }}
- External access: {{ remote_access or external_access or "(from presales)" }}
- VCF domains: {{ vcf_domains or "(from presales)" }}

## Phases (EPDIO)
- Engage / Plan / Design / Implement / Operate

## Deliverables
- HLD, LLD, Implemented Horizon, ATP results, As-Built, KT

## Acceptance Criteria
- ATP executed successfully; configuration aligns with approved LLD.
""",
    "hld.md.j2": """# High-Level Design
**Project:** {{ project_name|default("Project") }}
**Customer:** {{ customer_name|default("Customer") }}

## Conceptual
Users connect via supported clients; identity via enterprise IdP; pools via Horizon.

## Logical
Connection Servers, Unified Access Gateway (if external), App Volumes, DEM, Events DB, vCenter integration.

## Physical
- VCF workload domains: {{ vcf_domains or "(from presales)" }}
- Regions: {{ regions or "(from presales)" }}
""",
    "loe.md.j2": """# Level of Effort (LOE)
**Project:** {{ project_name|default("Project") }}
**Customer:** {{ customer_name|default("Customer") }}

## Effort by Phase (EPDIO)
- Engage: 6 hours
- Plan: 8 hours
- Design: 14 hours
- Implement: 32 hours
- Operate: 12 hours

**Total Estimated Hours:** 72
""",
}

def _env(template_root: Path) -> Environment:
    loaders = []
    if template_root.exists():
        loaders.append(FileSystemLoader(str(template_root)))
    loaders.append(DictLoader(INLINE_TEMPLATES))
    return Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(enabled_extensions=("html","xml"))
    )

def _render_md(env: Environment, name: str, ctx: Dict) -> str:
    tpl = env.get_template(name)
    return tpl.render(**ctx, now=datetime.utcnow())

def _run(cmd: str, cwd: Optional[Path]=None) -> None:
    proc = subprocess.run(shlex.split(cmd), cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {cmd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

def ensure_pandoc() -> None:
    # Check pandoc availability
    try:
        _run("pandoc --version")
    except Exception as e:
        raise RuntimeError("Pandoc is not installed or not on PATH. Please install pandoc and retry.") from e

def md_to_docx(md_text: str, out_docx: Path, reference_docx: Optional[Path]=None) -> None:
    out_docx.parent.mkdir(parents=True, exist_ok=True)
    tmp_md = out_docx.with_suffix(".tmp.md")
    tmp_md.write_text(md_text, encoding="utf-8")
    cmd = f"pandoc {shlex.quote(tmp_md.name)} -o {shlex.quote(out_docx.name)}"
    if reference_docx and reference_docx.exists():
        cmd += f" --reference-doc={shlex.quote(str(reference_docx))}"
    _run(cmd, cwd=out_docx.parent)
    try:
        tmp_md.unlink()
    except Exception:
        pass

def generate_phase1_docs(ctx: Dict, outdir: Path, template_root: Path, reference_docx: Optional[Path]=None) -> Dict[str, Path]:
    """
    Render SOW/HLD/LOE using Jinja2+Markdown and convert to DOCX via Pandoc.
    - template_root: typically templates/docgen/
    - reference_docx: optional Word styles file for consistent WWT look
    Returns dict with keys SOW,HLD,LOE and ZIP
    """
    ensure_pandoc()
    env = _env(template_root)
    outdir.mkdir(parents=True, exist_ok=True)

    # Output filenames (kept short; your app already maps/whitelists them)
    sow_path = outdir / "SOW.docx"
    hld_path = outdir / "HLD.docx"
    loe_path = outdir / "LOE.docx"

    sow_md = _render_md(env, "sow.md.j2", ctx)
    hld_md = _render_md(env, "hld.md.j2", ctx)
    loe_md = _render_md(env, "loe.md.j2", ctx)

    md_to_docx(sow_md, sow_path, reference_docx)
    md_to_docx(hld_md, hld_path, reference_docx)
    md_to_docx(loe_md, loe_path, reference_docx)

    # Optional zip for convenience
    zip_path = outdir / "Phase1.zip"
    import zipfile
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (sow_path, hld_path, loe_path):
            z.write(p, arcname=p.name)

    return {"SOW": sow_path, "HLD": hld_path, "LOE": loe_path, "ZIP": zip_path}
