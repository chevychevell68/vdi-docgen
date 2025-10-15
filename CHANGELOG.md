# Changelog

All notable changes to this project will be documented in this file.

## v1.2.1 — 2025-10-15

### Added
- History table: sortable columns, global search, and per-column filters.
- Company and Project both clickable (link to `/presales/view/<id>`).

### Changed
- Document titles and filenames now use **Company** and **Project** consistently.
- Submission page buttons show product names (SOW/HLD/LOE/etc.) instead of raw filenames.

### Fixed
- Button label/file-name mismatch on submission page.
- Template variables for titles normalized to prevent Pandoc YAML header parsing issues.

## v1.2 — 2025-10-15
- Major cleanup to doc generation; Pandoc + Jinja flow standardized.
- PDG ingest (optional) flow: map PDG fields to presales JSON; merge only blanks.
- Safer download routing; optional GitHub mirroring for submissions.
