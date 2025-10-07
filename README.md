# VDI DocGen — Clean Replacement

Minimal Flask app with Presales and PDG.

## Routes
- `/` or `/presales` — Presales questionnaire → review → Download Markdown
- `/pdg`           — Choose Single/Multi → PDG form → review → Download .docx
- `/predeploy`     — Redirects to `/pdg`
- `/__version` and `/__health` — deployment canaries

## Render
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn app:app
- Root Directory: repo root
