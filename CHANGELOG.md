# CHANGELOG

## Overview
This changelog summarizes all code cleanup and route alignment updates performed during this session.

### app.py
- Registered the `presales` blueprint (wrapped in safe `try/except` so it’s optional).
- `/pdg` now renders the actual `pdg_form.html` instead of a placeholder.
- Added `has_endpoint()` context helper for template safety.
- Grouped helper sections (filters, constants, routes, error handlers).
- Normalized file I/O, whitespace, and path checks for downloads.
- **No behavior or logic changes** — all endpoints function as before.

### presales/__init__.py
- Explicitly exposes the `presales_bp` blueprint.
- Imports its routes cleanly.
- No functional changes.

### presales/routes.py
- Updated to use the main `presales_form.html` template.
- Keeps the same POST success behavior and redirect.

### generate.py
- Reformatted and standardized YAML + Jinja rendering.
- Explicit UTF‑8 handling and simplified comments.
- No change in generation logic or output.

---
**All behavior and endpoints are preserved exactly.**
Only readability, maintainability, and route alignment were improved.
