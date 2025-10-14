\
VDI-DocGen ctx patch
====================

This package gives you a working `ctx` pipeline plus a safe download route.

What you get
------------
1) `app.py`
   - Minimal Flask app that demonstrates:
     * Saving a submission snapshot to `generated/submissions/<sid>.json`
     * Building/saving a context file `generated/submissions/<sid>-ctx.json`
     * `/presales/view/<sid>` always passes `ctx` (rebuilds it if missing)
     * `/download/<sid>/<filename>` only serves deliverables whitelisted in `ctx`
   - Replace or merge these helpers/routes into your project.

2) `templates/presales_submitted.html`
   - Dual-mode template:
     * Prefers `ctx.deliverables` for download buttons
     * Falls back to legacy `docx_available` if `ctx` is missing
     * Shows a JSON dump of the submission for quick validation

Run locally (demo)
------------------
- Place some `.docx` files into `output-docx/` (e.g., ACME-HLD.docx, ACME-LLD.docx).
- Start the server:
    export PORT=5000
    python app.py
- Open http://localhost:5000, submit the demo form, then you'll be redirected to
  `/presales/view/<sid>` with working download buttons.

Integrate into your app (merge strategy)
----------------------------------------
If your project already has blueprints and routes:
1) Copy these functions into your main app (or a helper module):
   - _now_str, _save_submission, _load_submission, _save_ctx, _load_ctx,
     _map_requested_docx, _human_title_from_filename
   - The directory constants: GEN_DIR, CTX_DIR, DOCX_DIR, DELIV_DIR
2) Ensure your submit route (e.g., `/presales/submit`) builds & saves `ctx` right after
   saving the raw submission JSON.
3) Ensure your view route (e.g., `/presales/view/<sid>`) *always* passes `ctx` to
   `render_template(...)`, rebuilding if the `-ctx.json` file is missing or corrupt.
4) Add the download route:
   @app.get("/download/<submit_id>/<path:filename>") -> send_from_directory(...)
5) Update your `presales_submitted.html` to use `ctx` (the included template is dual-mode).

Notes
-----
- Directories created on startup:
  - generated/submissions/      (submission snapshots + ctx files)
  - output-docx/                (expected location for generated docx files)
  - output/                     (optional extra artifacts like .md, .zip)
- If your generator runs async (e.g., GitHub Action), revisiting
  `/presales/view/<sid>` will refresh the `ctx` to include newly appeared DOCX files.
- The download route is intentionally strict: it only serves files found in `ctx.deliverables`.

Happy shipping!
