"""
docgen.py — Minimal Pandoc-based Markdown→DOCX helpers for VDI-DocGen.

Safe to drop into the repo root. Requires:
  - pandoc (binary) available on PATH
  - Flask request context when calling render_markdown (call from a route)
"""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from flask import current_app, render_template

OUTPUT_DIR = Path("output")
DOCX_DIR   = Path("output-docx")
TEMPLATE_PREFIX = "md/"           # we render templates like md/SOW.md.j2
REFERENCE_DOCX  = "styles/reference.docx"  # optional; Pandoc works without it

def _ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCX_DIR.mkdir(parents=True, exist_ok=True)

def render_markdown(template_name: str, context: Dict[str, Any]) -> str:
    """Render a Jinja Markdown template within a Flask request context."""
    return render_template(f"{TEMPLATE_PREFIX}{template_name}", **context)

def write_markdown(basename: str, markdown: str) -> Path:
    """Write Markdown to output/<basename>.md and return the path."""
    _ensure_dirs()
    path = OUTPUT_DIR / f"{basename}.md"
    path.write_text(markdown, encoding="utf-8")
    return path

def md_to_docx(md_path: Path, docx_name: str, reference: str = REFERENCE_DOCX) -> Path:
    """Call Pandoc to convert Markdown → DOCX into output-docx/<docx_name>."""
    _ensure_dirs()
    out = DOCX_DIR / docx_name
    cmd = ["pandoc", str(md_path), "-o", str(out)]
    if Path(reference).exists():
        cmd += [f"--reference-doc={reference}"]
    # You can add filters here if needed, e.g., --from=gfm
    subprocess.run(cmd, check=True)
    return out

def build_phase1_docs(data: Dict[str, Any]) -> List[str]:
    """Render SOW/HLD/LOE/PDG from presales data and convert to DOCX.
    Returns list of generated filenames.
    """
    created: List[str] = []
    ctx = {"data": data}
    pairs = [
        ("SOW", "SOW.docx"),
        ("HLD", "HLD.docx"),
        ("LOE", "LOE.docx"),
        ("PDG", "PDG.docx"),
    ]

    for base, docx_name in pairs:
        md_text = render_markdown(f"{base}.md.j2", ctx)
        md_path = write_markdown(base, md_text)
        md_to_docx(md_path, docx_name)
        created.append(docx_name)

    current_app.logger.info("Phase‑1 docgen complete: %s", created)
    return created
