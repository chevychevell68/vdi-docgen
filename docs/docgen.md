# Document Generation (Pandoc + Jinja)

Templates live in `doc_templates/` and end with `.md.j2`. They produce Pandoc-ready Markdown.

## Steps
1. `render_template("sow.md.j2", **data)` → yields `SOW.tmp.md`
2. `pandoc SOW.tmp.md -o SOW.docx --reference-doc=<PANDOC_REFERENCE_DOCX>`

## Title & Front Matter
We **do not** rely on Pandoc YAML metadata blocks for title/author. Instead, we render titles as standard Markdown (H1/H2/etc.) to avoid YAML type errors. Example:

```markdown
# Statement of Work
**{{ company_name or "Customer" }}**  
{{ project_name or sf_opportunity_name or "Project" }}  
{{ now.strftime("%B %d, %Y") }}
```

## Adding a New Doc
- Create `doc_templates/<name>.md.j2`
- Register a button on `presales_submitted.html` if desired
- Use the same variable keys as the presales form

