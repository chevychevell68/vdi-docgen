# Developer Workflow & Guardrails

1. **Do not delete** existing routes or helpers used by templates (`has_endpoint`, filters).
2. Keep `doc_templates/*.md.j2` minimal and rely on `reference/wwt-reference.docx` for formatting.
3. When changing form field names, update:
   - `presales_form.html` (input `name` attributes)
   - Templates in `doc_templates/`
   - Any mapping code (e.g., PDG merge map)
4. To add a new deliverable:
   - Put a `.md.j2` in `doc_templates/`
   - Add a label->filename entry in the map used for zips
   - Add a button on `presales_submitted.html` if you want a top-level download
5. Keep **button labels** stable (SOW/HLD/LOE/WBS…) to avoid long/ugly UI text.
6. All per-submission outputs live under `output/output-docx/<id>/`.
