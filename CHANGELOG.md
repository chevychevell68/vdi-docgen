## v1.2.3 - 2025-10-20
### Updates
- Presales Form (Directory & Core Services) layout separated and cleaned
- Added conditional "Storage → Other" input with dynamic toggle
- Improved numeric field formatting
- Updated all UI pages and docs to reflect version v1.2.3
- Synced documentation and templates for consistency

# Changelog

## v1.2.3 – 2025-10-17

### Added
- **Audit trail** for Presales submissions: each edit captures timestamp and per-field changes in `"_revisions"`.
- **Change history UI** on *Presales Data* page with collapsible details (field, before, after).
- **Last updated** timestamp displayed alongside original Submitted time.

### Changed
- **History page**: Status column visible and filter/sortable by any present values.
- **Edit flow**: Editing preserves original `__submitted_at__` while updating `_saved_at`.

### Fixed
- **Duplicate records on edit**: form now includes hidden `_id` so saves update the original JSON instead of creating a new one.
- **Status header alignment** and minor UI inconsistencies.

All notable changes to this project will be documented in this file.

## v1.2.3 — 2025-10-15

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