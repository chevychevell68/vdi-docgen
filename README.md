# VDI‑DocGen 1.2.1 (MVP) — Project Overview

This repository contains the MVP for **VDI‑DocGen**: a Flask application that collects presales inputs and generates customer‑ready deliverables (DOCX/ZIP) using a Jinja→Markdown→Pandoc pipeline. This document gives a quick start for local/dev use and links to deeper docs in `docs/`.

## Quick Start

### Requirements
- Python 3.11+
- pandoc (for Markdown → DOCX)
- (Optional) `docx`/`python-docx` if using direct document composition modes
- (Optional) GitHub token for mirroring submissions

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
# Ensure pandoc is installed and on PATH: `pandoc -v`
```

### Run

```bash
export FLASK_ENV=development
export FLASK_APP=app.py
flask run --host 0.0.0.0 --port 5000
```

Or with gunicorn:

```bash
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

Once running, open http://localhost:5000 and use the **Presales** form.

### Primary Directories (default)
- `submissions/` — authoritative snapshots of each submission (JSON)
- `generated/` — submission contexts & exports (ZIPs under `generated/exports/`)
- `output/` — Markdown/temporary artifacts
- `output-docx/` — final DOCX deliverables

### Common Environment Variables
- `OUTPUT_DIR` (default: `output`)
- `DELIV_DIR` (default: `generated`)
- `DOCX_DIR` (default: `output-docx`)
- `EXPORTS_DIR` (default: `generated/exports`)
- `SUBMIT_DIR` (default: `submissions`)
- `GITHUB_TOKEN`, `DEFAULT_REPO`, `DEFAULT_BRANCH` (optional mirroring)

## What to read next
- `docs/ARCHITECTURE.md` — high level system design, data flow
- `docs/ROUTES.md` — full endpoint catalog and behaviors
- `docs/DELIVERABLES.md` — deliverable catalog, naming, and where files land

### Development Rules for vdi-docgen

**Core Principles**
- Deliver full, ready-to-run files or ZIPs — no snippets, diffs, or partial patches.
- Do not overwrite working code; all changes must be additive or explicitly approved.
- Treat each modification as a versioned update (vX.Y.Z).
- Always preserve `ctx` logic, file structure (`/templates`, `/generated`, `/static`), and working Flask routes.

**Templates & UI**
- Retain all Jinja macros and structure (`{% extends "base.html" %}`, `{% block content %}`).
- Maintain visual consistency (field widths, disclaimer text, alignment).
- Add new fields or options only where relevant; do not expand unrelated sections.

**Output & Files**
- Generated outputs must include timestamps and unique submission IDs.
- All downloadable files must have correct extensions.
- If multiple files are touched, deliver as a single ZIP package.
- Do not render huge files inline — provide download links instead.

**Workflow Discipline**
- No regressions of previous fixes or logic.
- Never rename stable files unless explicitly approved.
- Keep a running changelog when possible.
- Ask before guessing or “auto-fixing.”

**Context Reminder**
This project is the Flask-based **WWT vdi-docgen** automation system for generating presales and design deliverables (Presales, PDG, SOW, HLD, LLD, etc.). All updates should align with WWT’s internal EPDIO and deliverable standards.


_Last updated: 2025-10-20_
