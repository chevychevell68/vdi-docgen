# Configuration & Environment

- `DOC_TEMPLATES_DIR` — directory containing `*.md.j2` (default: `./doc_templates`)
- `PANDOC_REFERENCE_DOCX` — Word styles reference (default: `./reference/wwt-reference.docx`)
- `PANDOC_PATH` — optional, explicit path to `pandoc` binary (else from PATH)
- `OUTPUT_DIR` — root output (default: `./output`)
- `DOCX_DIR` — generated `.docx` (default: `$OUTPUT_DIR/output-docx`)
- `EXPORTS_DIR` — zip exports (default: `$OUTPUT_DIR/exports`)
- `SUBMIT_DIR` — local submissions store (default: `./submissions`)
- `GITHUB_TOKEN` — optional PAT for mirroring submissions
- `DEFAULT_REPO` — optional `"owner/repo"` for mirroring
- `DEFAULT_BRANCH` — optional branch (default: `main`)

### Required Binaries
- `pandoc` must be installed and available in PATH (or set `PANDOC_PATH`).

### Jinja Filters Registered
- `fmt_bool`, `none_to_empty`, `lines`

