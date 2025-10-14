# VDI‑DocGen — **Authoritative System Guide** (for ChatGPT)
**Version:** v4 • **Updated:** 2025-10-14T20:01:31Z • **Baseline branch:** restore‑pre‑docgen

This document is the single source of truth for how THIS app is supposed to work. It exists so future ChatGPT sessions don’t guess, rename things, or rewire flows mid‑development.

---

## 0) Big‑Picture Intent (confirmed by user)
- Take **presales intake** → persist a **snapshot** → render **Markdown** per deliverable → convert to **DOCX (via Pandoc)** → present consistent **download links**.
- **PDG loop:** Output a customer‑facing PDG DOCX, they complete it, we **upload** it to enrich context, then we generate the **implementation set**.
- **LOE vs WBS are distinct:**
  - **LOE (Level of Effort)** = **high‑level** estimate snapshot (hours, roles, major work areas) used by the **solutions tool**.
  - **WBS (Work Breakdown Structure)** = **low‑level** task list (phases → tasks → sub‑tasks), goes into a project plan.

---

## 1) Canonical End‑to‑End Workflow
1. **Presales intake (form)** → user enters environment details.
2. **Persist snapshot** → write `generated/submissions/<sid>.json` (ground truth).
3. **Render Markdown** (Jinja → Markdown) for Phase‑1 deliverables:
   - `templates/md/SOW.md.j2` → `output/SOW.md` → **Pandoc** → `output-docx/SOW.docx`
   - `templates/md/HLD.md.j2` → `output/HLD.md` → Pandoc → `output-docx/HLD.docx`
   - `templates/md/LOE.md.j2` → `output/LOE.md` → Pandoc → `output-docx/LOE.docx`
   - `templates/md/PDG.md.j2` → `output/PDG.md` → Pandoc → `output-docx/PDG.docx`
   - *(If a combined LOE/WBS existed previously, we now split them. WBS is **not** produced in Phase‑1.)*
4. **Deliver PDG to customer** → customer fills it and returns.
5. **Upload PDG** → we parse/merge into submission context.
6. **Render Phase‑2 Markdown** → convert to DOCX:
   - `templates/md/LLD.md.j2` → `output/LLD.md` → Pandoc → `output-docx/LLD.docx`
   - `templates/md/ATP.md.j2` → `output/ATP.md` → Pandoc → `output-docx/ATP.docx`
   - `templates/md/WBS.md.j2` → `output/WBS.md` → Pandoc → `output-docx/WBS.docx` (low‑level task plan)
7. **Submission Complete page** lists available DOCX and offers ZIP of requested files.

**Filenames (UI contract, fixed):**
- **Phase‑1:** `SOW.docx`, `HLD.docx`, `LOE.docx`, `PDG.docx`
- **Phase‑2:** `LLD.docx`, `ATP.docx`, `WBS.docx`

> We previously used `LOE-WBS.docx`. That is superseded by **two** docs: `LOE.docx` and `WBS.docx`.

---

## 2) Directories & Files
- `generated/submissions/<sid>.json` — presales snapshot (immutable ground truth).
- `generated/submissions/<sid>-ctx.json` — **ctx** context that powers results page (deliverables list).
- `templates/md/*.md.j2` — Markdown Jinja templates per deliverable (Phase‑1 and Phase‑2).
- `styles/reference.docx` — Pandoc **reference DOCX** for consistent Word styling.
- `output/*.md` — intermediate Markdown exports (debuggable, human‑readable).
- `output-docx/*.docx` — **final** Word deliverables with the fixed filenames above.

---

## 3) Routing, Linking, and ctx Behavior (do not change without approval)
**Submit flow**
- `POST /presales/submit`:
  1) Save snapshot to `generated/submissions/<sid>.json`.
  2) (When generation is enabled) call `build_phase1_docs(data)` which renders Markdown and runs Pandoc to create DOCX into `output-docx/`.
  3) Build/refresh **ctx**:
     ```json
     {
       "sid": "<sid>",
       "submitted_at": "ISO8601",
       "data": {...},
       "deliverables": [
         {"filename": "SOW.docx", "title": "SOW"},
         {"filename": "HLD.docx", "title": "HLD"}
         ...
       ],
       "docx_dir": "output-docx/"
     }
     ```
  4) Redirect to `/presales/view/<sid>`.

**Results page**
- `GET /presales/view/<sid>`:
  - Always loads **ctx** (and rebuilds if missing), then `render_template("presales_submitted.html", data=obj, ctx=ctx, ...)`.
  - **Templates must prefer `ctx.deliverables`**; legacy variables may exist for backward compat.

**Downloads & ZIP**
- `GET /download/<sid>/<filename>` — serves only files listed in `ctx.deliverables` from `output-docx/` (whitelist).
- `GET /presales/zip/<sid>` — bundles requested DOCX found in `output-docx/`.

**PDG Upload**
- `POST /pdg/upload/<sid>` (to be implemented):
  - Accepts PDG (DOCX or structured JSON exported from the PDG).
  - Parses fields → merges into context → persists `generated/submissions/<sid>-pdg.json` or updates `data` within ctx (tracked field for provenance).
  - Triggers Phase‑2 generation (LLD/ATP/WBS) with the augmented context.
  - Refreshes ctx and redirects to `/presales/view/<sid>` (links now include Phase‑2 files).

---

## 4) Pandoc‑based Generation (chosen path)
**Why Pandoc?** We used it before; templates are Markdown; reference DOCX preserves style globally; minimal new Python deps.

**Runtime requirement**
- System binary: `pandoc` must be installed and in PATH.

**Template model**
- Location: `templates/md/*.md.j2`
- Context object: the **presales snapshot** (`data`) plus simple derived values.
- Rendering helpers (Python):  
  - `render_markdown(template, context) -> str`  
  - `write_markdown(name, text) -> Path("output/NAME.md")`  
  - `md_to_docx(md_path, docx_name, reference="styles/reference.docx") -> Path("output-docx/NAME.docx")`  
  - `build_phase1_docs(data)` → returns a list of created filenames  
  - `build_phase2_docs(data_with_pdg)` → returns LLD/ATP/WBS filenames

**Styling**
- Pandoc will use `styles/reference.docx`. Keep this in repo and version it.

---

## 5) Runbook (Dev & Prod)
**Development (Codespaces)**
```bash
pkill -f gunicorn || true; pkill -f flask || true
python -m pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_ENV=development
export PORT=${PORT:-5000}
python -m flask run --host=0.0.0.0 --port=$PORT
```

**Prod‑like**
```bash
python -m pip install --upgrade --force-reinstall gunicorn
export PORT=${PORT:-5000}
python -m gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level info
```

**Pandoc install (Debian/Ubuntu example)**
```bash
sudo apt-get update && sudo apt-get install -y pandoc
pandoc --version
```

---

## 6) Guardrails (for ChatGPT — do not violate)
- **Do not** change form fields or rename outputs without explicit instruction.
- Preserve existing route names and template variables.
- `ctx` is additive and rebuildable; keep legacy paths working.
- Deliverable filenames **must** match the fixed list above (Phase‑1 & Phase‑2).

---

## 7) Next Steps (Implementation Order)
1) Add `templates/md` for **SOW/HLD/LOE/PDG** (Phase‑1).
2) Add `docgen.py`: helpers + `build_phase1_docs()`.
3) Call `build_phase1_docs(data)` inside `/presales/submit` (after writing `<sid>.json`).
4) Confirm DOCX appear in `output-docx/` and in the results page via `ctx`.
5) Add PDG upload endpoint + parser, then `build_phase2_docs()` for **LLD/ATP/WBS**.
