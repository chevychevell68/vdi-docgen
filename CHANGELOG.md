# Change Log

All notable changes to this project will be documented in this file.

---

## [v1.1.3] – Convert Yes/No Questions to Checkboxes
### Added
- Automatically converts Yes/No **radio** or **select** groups into a single checkbox with hidden `"Yes"` value.
- Checkbox appears before the question text for intuitive UX.
- When checked, the hidden field submits `"Yes"`; when unchecked, no value is sent.

### Maintained
- Required-field asterisks and smart placeholder logic remain intact.

### Deployment
- Commit: `v1.1.3`
- Branch: `v1.1.1` (active dev)
- Released: 2025-10-08

---

## [v1.1.2] – Add Sample Placeholder Text
### Added
- Auto-injected sample placeholder text for all Presales form fields (centralized in `base.html`).
- Common examples include:
  - Numeric fields → `e.g., 250`
  - URL fields → `https://your-instance.example.com/...`
  - Percent fields → `e.g., 20`
  - Factor fields → `e.g., 1.10`
- Added a “Select...” default option to dropdowns for better UX.

### Maintained
- Required-field asterisks from v1.1.1 remain fully functional.

### Deployment
- Commit: `v1.1.2`
- Branch: `v1.1.1`
- Released: 2025-10-08

---

## [v1.1.1] – Required Field Asterisks
### Added
- Automatically adds a red asterisk (`*`) next to all required form fields.
- Implemented globally via JavaScript in `base.html`, without editing templates individually.

### Deployment
- Commit: `efb94cc`
- Branch: `v1.1.1`
- Released: 2025-10-08

---

## [v1.1.0] – Stable Baseline
### Established
- First stable version of the Presales form generator with Markdown/Word export.
- Routes:
  - `/presales` (Presales Discovery Form)
  - `/pdg` (Project Definition Guide)
  - `/predeploy` (Pre-Deployment)
- Added GitHub integration for submission persistence.
- Implemented required field validation and vSAN / density calculations.
- Added automatic document packaging (`SOW`, `HLD`, `LOE/WBS`, `ROM`) into downloadable ZIP.

### Deployment
- Commit: `504fa67`
- Branch: `main`
- Released: 2025-10-07
