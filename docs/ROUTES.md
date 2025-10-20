# Routes

This file catalogs the major endpoints and their intent. Exact parameter names and payloads may vary slightly depending on the form templates; this reference is accurate for the MVP line.

> Methods are shown in parentheses.

## Core

- `/` (GET) — Home/landing; links to Presales and History.
- `/presales` (GET) — Main Presales form.
- `/presales/submit` (POST) — Create a new submission snapshot in `submissions/`. Computes diffs if editing.
- `/presales/view/<submit_id>` (GET) — View a submission results page (download links, context table).
- `/presales/edit/<submit_id>` (GET/POST) — Edit flow; merges inputs and appends to `"_revisions"`.
- `/history` (GET) — History table of existing submissions found in `submissions/`.

## Downloads

- `/download/<submit_id>/<filename>` (GET) — Safe file download endpoint. Whitelisted filenames only.
- `/download/md/<name>` (GET) — Download Markdown artifacts (if present).
- `/download/docx/<name>` (GET) — Download a DOCX by conventional name from `output-docx/`.

## Bundling / Exports

- `/presales/zip/<submit_id>` (GET) — Build and return a ZIP export into `generated/exports/`.
- `/exports` (GET) — List available ZIP exports.

## PDG (optional helper)

- `/pdg` (GET) — PDG landing/form.
- `/pdg/submit` (POST) — Receives PDG inputs (stored similarly to presales submissions).
- `/presales/upload-pdg/<submit_id>` (POST) — Attach PDG artifact(s) to an existing submission.

## Notes

- The templates use a `ctx` object for the results page to decide which deliverables exist vs. were requested.
- Missing `ctx` in legacy routes is handled defensively by showing generic deliverables, but you should prefer `/presales/view/<id>` which always passes `ctx`.
