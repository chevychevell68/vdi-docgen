# ARCHITECTURE.md — VDI‑DocGen (restore‑pre‑docgen)

This file is a terse reference for system design—kept alongside the main README for fast orientation.

## Components
- **Flask App (`templates/app.py`)**: registers routes, renders templates, writes snapshots.
- **Templates (`templates/`)**: Jinja2 views for forms and submission results.
- **Outputs**
  - `generated/submissions/<sid>.json` — raw presales snapshot
  - `output-docx/*.docx` — generated documents
  - `output/*.md` — optional Markdown audits
- **(Optional) ctx**: `generated/submissions/<sid>-ctx.json` passed as `ctx` to templates to drive download UI.

## Data Flow
User → `/presales/new` → POST `/presales/submit` → write JSON → list DOCX in `output-docx` → render results page with download links.

## Non‑Goals
- Do not rename or rewire forms without explicit direction.
- Do not introduce breaking template changes; preserve legacy variables.

## Deployment
- Dev: `python -m flask run`
- Prod: `python -m gunicorn app:app …` or `Procfile` (Render/Heroku).
