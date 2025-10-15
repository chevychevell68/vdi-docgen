# VDI DocGen — v1.2.1

This repository generates WWT-style project documents (SOW, HLD, LOE/WBS, PDG, etc.) from a **Horizon Presales Discovery** form.
It renders Word documents via **Pandoc** + **Jinja2** using Markdown templates in `doc_templates/`, and stores submissions locally in `submissions/` (and optionally mirrors them to GitHub).

## TL;DR (How to run)

```bash
# (optional) python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
export DOC_TEMPLATES_DIR="${DOC_TEMPLATES_DIR:-$PWD/doc_templates}"
export PANDOC_REFERENCE_DOCX="${PANDOC_REFERENCE_DOCX:-$PWD/reference/wwt-reference.docx}"
export OUTPUT_DIR="${OUTPUT_DIR:-$PWD/output}"
export DOCX_DIR="${DOCX_DIR:-$OUTPUT_DIR/output-docx}"
export EXPORTS_DIR="${EXPORTS_DIR:-$OUTPUT_DIR/exports}"
export SUBMIT_DIR="${SUBMIT_DIR:-$PWD/submissions}"
export DEFAULT_REPO=""         # optional: "owner/repo"
export DEFAULT_BRANCH="main"   # optional
export GITHUB_TOKEN=""         # optional PAT if mirroring submissions

python app.py
# open http://localhost:5000
```

## What changed in v1.2.1

- **History page** now shows **Company** then **Project**; both link to the submission.
- Client-side **sorting, search, and filters** on the history table.
- Document generation: titles now use **Company** and **Project** correctly (SOW/HLD/LOE).
- Buttons on the submission page show **labels** (SOW/HLD/LOE/etc.) while downloading
  the **customer-/project-named** files.
- Documentation refreshed (this bundle) to capture the current architecture and workflow.

See `CHANGELOG.md` for a complete list.

## Project Structure

```
.
├─ app.py                         # Flask app (vv1.2.1)
├─ templates/                     # Jinja2 HTML templates
│  ├─ base.html
│  ├─ index.html
│  ├─ presales_form.html          # presales intake form (includes new Project Name field)
│  ├─ presales_submitted.html     # submission detail + doc buttons
│  ├─ history.html                # searchable/sortable history table (Company, Project links)
│  ├─ pdg_form.html
│  ├─ pdg_upload.html
│  ├─ exports.html
│  └─ …
├─ doc_templates/                 # **Pandoc/Jinja** Markdown templates (SOW, HLD, LOE, …)
│  ├─ sow.md.j2
│  ├─ hld.md.j2
│  ├─ loe.md.j2
│  ├─ wbs.md.j2                   # phase-2 WBS (future)
│  └─ shared/                     # partials, fragments (if used)
├─ reference/
│  └─ wwt-reference.docx          # Word reference styles for consistent WWT look/feel
├─ output/                        # runtime output root (configurable via env)
│  ├─ output-docx/                # generated .docx files
│  │  └─ <submission_id>/         # files for a specific submission
│  └─ exports/                    # exported .zip bundles
├─ submissions/                   # json snapshots of form submissions
├─ requirements.txt
├─ README.md                      # (this file)
└─ docs/                          # deeper technical docs (see below)
```

> **Important:** `DOC_TEMPLATES_DIR` and `PANDOC_REFERENCE_DOCX` must point
> to real paths. Use the defaults above for local dev.

## Core Concepts

- **Presales form** captures everything needed to render SOW/HLD/LOE. A new field **Project Name** is now included and used in titles and filenames.
- **Templates** are Markdown with Jinja2 (`*.md.j2`), rendered to `.docx` via **Pandoc** using a reference stylesheet (`wwt-reference.docx`) to match WWT branding.
- **Filenames** are created with a **short code** built from Company + Project to keep paths readable (e.g., `HAWAII-PACAF_HZN6SITES-HLD.docx`), while **UI buttons** always show **SOW/HLD/LOE** labels.
- **Submissions** persist under `submissions/` and are listed on **/history**, which links to **/presales/view/<id>**.

## Developer Workflow

1. Make template edits in `doc_templates/`, keep variable names in sync with the presales form keys.
2. Restart the Flask app and **re-generate** documents by revisiting the submission page and clicking **Regenerate Docs** (if present) or creating a new submission.
3. Validate output in `output/output-docx/<submission_id>/`.
4. Keep `reference/wwt-reference.docx` as the visual source of truth for Word styles.

See `docs/` for full details.
