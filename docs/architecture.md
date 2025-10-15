# Architecture Overview

The app is a single Flask service using:
- **Flask + Jinja2** for web UI and HTML templates
- **Pandoc** to convert Markdown to Word (`.docx`), applying **reference/wwt-reference.docx** for WWT styles
- **Jinja2 Markdown templates** in `doc_templates/` to produce Pandoc-ready Markdown
- **Local JSON persistence** in `submissions/` for each form submission

High-level flow:
1. User fills **/presales** → POST to **/presales/submit**.
2. JSON is saved under `submissions/<id>.json`.
3. Submission detail page **/presales/view/<id>** renders buttons (SOW/HLD/LOE…).
4. On generate/regenerate, the server renders `*.md.j2` → Pandoc → `.docx` saved to `output/output-docx/<id>/`.
5. Downloads route serves the `.docx` via `/download/<id>/<filename>`.

### Naming & Short Codes
- We compute short codes from **Company** and **Project Name** for filenames.
- UI always shows **SOW/HLD/LOE** labels to avoid very long button text.
