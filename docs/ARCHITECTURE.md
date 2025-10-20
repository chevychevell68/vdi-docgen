# Architecture

This document describes how **VDI‑DocGen** is organized and how data flows through the system. The goal is to help new contributors navigate the codebase quickly without changing runtime behavior.

## High‑Level Flow

1. **User submits Presales form** → server validates & normalizes inputs.
2. **Submission snapshot** is written into `submissions/<id>.json` as the authoritative record.
3. **Revision tracking** keeps an audit trail for edits under `"_revisions"`.
4. **Context builder** collects requested deliverables and checks which DOCX files exist.
5. **Results page** shows download buttons for present docs and a list of requested‑but‑missing docs.
6. **Generation pipeline (Pandoc)** can produce DOCX into `output-docx/` from Markdown templates.
7. **One‑click ZIP** bundles relevant artifacts into `generated/exports/<id>.zip`.

## Key Modules

- **`app.py`** — Flask app factory + routes for submit/view/edit/history/download/zip/exports and PDG helpers.
- **`presales/` (package)** — light form‑render route; does not duplicate the above logic.
- **`pandoc_gen.py`** — Jinja→Markdown→Pandoc generation utilities.
- **`docgen.py` / `docgen_phase1.py`** — helper functions for naming/writing/templating.
- **`templates/`** — Jinja templates for UI (forms, results, history).

> Note: There is also a top‑level `presales.py` file present in some snapshots. Because there is a `presales/` **package**, Python prefers the package import path, so that file's routes are **not** active. We keep it for reference; consolidation can happen later.

## Data & Storage

- **Submissions**: `submissions/<id>.json` (authoritative); contains:
  - `_id`, `__submitted_at__`, `_saved_at`
  - `_revisions`: list of edit events with timestamps and field‑level diffs (excluding ignored keys)
- **Artifacts**:
  - `output/` — intermediate Markdown or analysis
  - `output-docx/` — final deliverables (DOCX) that are linked to from the results page
  - `generated/exports/` — downloadable ZIP bundles per submission

## Deliverables

The UI assumes a **flat** `output-docx/` directory containing generated files with conventional names (see `docs/DELIVERABLES.md`). The results page compares **requested** vs **present** and displays appropriate actions.

## Extensibility Principles

- **Additive changes only**: new routes, templates, or files must not break or replace existing behaviors.
- **Source of truth**: submission JSON remains canonical; everything else is derived or supplemental.
- **Pure functions**: context & generation utilities should be deterministic given input.
- **Loose coupling**: generation pipeline is optional; the UI honors already‑present DOCX files.
