# Routes & Views

- `GET  /` → index
- `GET  /presales` → presales_form.html
- `POST /presales/submit` → save JSON → redirect to `/presales/view/<id>`
- `GET  /presales/view/<id>` → submission details + doc buttons
- `GET  /presales/zip/<id>` → zip all available `.docx`
- `GET  /download/<id>/<filename>` → safe download for known docx
- `GET  /pdg` → PDG quick form (optional)
- `POST /pdg/submit`
- `GET|POST /presales/upload-pdg/<id>` → upload PDG `.docx`, parse + merge
- `GET  /history` → sortable/searchable listing of submissions (Company, Project, Submitted at)

> Some routes are guarded in templates with `has_endpoint(...)` so templates can hide links when not registered.
