# Troubleshooting

- **Pandoc not found**: Install it or set `PANDOC_PATH` to the binary path.
- **'fmt_bool' is undefined**: Ensure `app.py` registers Jinja filters before template rendering.
- **Buttons missing**: Ensure `ctx.deliverables` or `docx_available` are populated; regenerate docs if needed.
- **Wrong titles**: Confirm `project_name` and `company_name` are captured; verify template uses these keys.
- **Download gives 404**: Confirm file exists in `output/output-docx/<id>/` and the filename matches the route.
