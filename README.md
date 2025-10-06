
# VDI DocGen (Presales + PDG)

Clean build with consistent UI, no CSV uploads, and PDG Word export.

## Routes
- `/` or `/presales` — Presales questionnaire → review → **Download Markdown**
- `/predeploy` — redirects to `/pdg`
- `/pdg` — select Single/Multi → PDG form → review → **Download .docx**

## Render settings
- **Root Directory**: (repo root)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
