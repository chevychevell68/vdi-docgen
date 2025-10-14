
VDI-DocGen — Pandoc Enablement Kit
==================================

Branch safety: You indicated you're on "pre-pandoc-enable".
Next, create a working branch:
    git checkout -b feature/pandoc-docgen

What this kit contains
----------------------
- docgen.py                        : helpers to render Markdown and call Pandoc for DOCX
- templates/md/SOW.md.j2          : robust skeleton (safe defaults)
- templates/md/HLD.md.j2          : robust skeleton
- templates/md/LOE.md.j2          : **high-level** LOE snapshot (not a task plan)
- templates/md/PDG.md.j2          : customer-facing questionnaire

Requirements
------------
- Pandoc installed and on PATH (`pandoc --version` must work).
- Optional style file at styles/reference.docx (Pandoc will work without it).

Minimal code change (3–6 lines)
-------------------------------
In your existing /presales/submit route, *after* you write `<sid>.json` and *before* redirecting:

```python
from docgen import build_phase1_docs

generated = []
try:
    generated = build_phase1_docs(data)  # data = the presales snapshot dict
except Exception as e:
    app.logger.exception("Phase-1 Pandoc generation failed: %s", e)

# If you are already building a ctx dict, extend or create deliverables like this:
# (Assuming ctx is a dict with a list under 'deliverables')
deliverable_objs = [{"filename": fn, "title": fn.rsplit(".", 1)[0]} for fn in generated]
if "ctx" in locals() and isinstance(ctx, dict):
    ctx.setdefault("deliverables", [])
    # append unique filenames
    existing = {d["filename"] for d in ctx["deliverables"]}
    for d in deliverable_objs:
        if d["filename"] not in existing:
            ctx["deliverables"].append(d)
else:
    # or create a fresh ctx if your app doesn't have one yet
    ctx = {
        "sid": submit_id,
        "submitted_at": data.get("__submitted_at__"),
        "data": data,
        "deliverables": deliverable_objs,
        "docx_dir": "output-docx",
    }

# If you have _save_ctx(...) helper, remember to persist it:
# _save_ctx(ctx)
```

No other routes, templates, or filenames change. Your results page should pick up the new DOCX via ctx (or your existing legacy listing).

Test checklist
--------------
1) Install Pandoc and verify:
    pandoc --version

2) Start the app and submit the presales form.
3) Confirm these files appear:
    output/SOW.md, output/HLD.md, output/LOE.md, output/PDG.md
    output-docx/SOW.docx, HLD.docx, LOE.docx, PDG.docx
4) Confirm the Submission Complete page shows the new links, and ZIP route bundles them.

Commit & push
-------------
    git add docgen.py templates/md/*.md.j2
    git commit -m "Enable Pandoc doc generation (Phase-1: SOW,HLD,LOE,PDG)"
    git push -u origin feature/pandoc-docgen
