# IMPLEMENTATION-PLAN.md — Enable Markdown→DOCX Generation with Pandoc

This plan enables document generation **without changing** your form, history, routes, or UI contracts.

## Requirements
- Pandoc binary installed and visible on PATH (`pandoc --version` works).
- `styles/reference.docx` checked into the repo for global styling (optional but recommended).

## Templates to add (Markdown Jinja)
Create `templates/md/` with:
- `SOW.md.j2`
- `HLD.md.j2`
- `LOE.md.j2`   # High-level effort snapshot for solutions tool
- `PDG.md.j2`   # Customer-facing questionnaire (Phase‑1)
- (Phase‑2, later) `LLD.md.j2`, `ATP.md.j2`, `WBS.md.j2` # WBS is the low-level task plan

Each template receives the same context dict: `data` (your presales snapshot) plus any derived fields.

## New module: docgen.py
Add `docgen.py` with the following helpers (approximate signatures):

```python
from pathlib import Path
import subprocess
from flask import render_template

OUTPUT_DIR = Path("output")
DOCX_DIR = Path("output-docx")
TEMPLATE_PREFIX = "md/"  # Jinja looks inside templates/

def render_markdown(template_name: str, context: dict) -> str:
    return render_template(f"{TEMPLATE_PREFIX}{template_name}", **context)

def write_markdown(basename: str, markdown: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{basename}.md"
    path.write_text(markdown, encoding="utf-8")
    return path

def md_to_docx(md_path: Path, docx_name: str, reference: str = "styles/reference.docx") -> Path:
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    out = DOCX_DIR / docx_name
    cmd = ["pandoc", str(md_path), "-o", str(out)]
    if Path(reference).exists():
        cmd += ["--reference-doc=" + reference]
    subprocess.run(cmd, check=True)
    return out

def build_phase1_docs(data: dict) -> list[str]:
    # Names map to fixed UI contract
    pairs = [
        ("SOW", "SOW.docx"),
        ("HLD", "HLD.docx"),
        ("LOE", "LOE.docx"),
        ("PDG", "PDG.docx"),
    ]
    created = []
    ctx = {"data": data}
    for base, docx_name in pairs:
        md = render_markdown(f"{base}.md.j2", ctx)
        md_path = write_markdown(base, md)
        md_to_docx(md_path, docx_name)
        created.append(docx_name)
    return created
```

## Wire-up in /presales/submit (minimal patch)
Inside your existing submit handler, **after** you save `<sid>.json`, add:

```python
from docgen import build_phase1_docs

try:
    generated = build_phase1_docs(data)
except Exception as e:
    app.logger.exception("Phase‑1 docgen failed: %s", e)
    generated = []

# Merge into ctx (deliverables append)
ctx_deliverables = [{"filename": fn, "title": fn.rsplit(".", 1)[0]} for fn in generated]
# ... then save ctx and redirect as you already do
```

This keeps everything else in your app intact (routes, templates, ZIP behavior).

## Testing
1) Ensure `pandoc --version` works.
2) Submit a form with SOW/HLD/LOE/PDG requested.
3) Verify `output/*.md` exist and `output-docx/*.docx` appear.
4) Confirm the results page shows the new links and ZIP includes them.

## Phase‑2 (after PDG upload is built)
- Add `build_phase2_docs(data_with_pdg)` mirroring Phase‑1, producing `LLD.docx`, `ATP.docx`, `WBS.docx`.
- Hook it up in the PDG upload route once the PDG parser merges answers into context.
