# Changelog

All notable changes to this project will be documented in this file.  
Versioning follows **MAJOR.MINOR.PATCH** (Semantic Versioning).

---

## [v1.1.1] – Current Development
### Added
- Automatic asterisk decoration for all required form fields (global via `base.html`).
- Branch created for isolated development and testing (`v1.1.1`).

### Deployment
- Render workspace configured to deploy from branch `v1.1.1`.
- Start command:
  ```bash
  gunicorn app:app --bind 0.0.0.0:$PORT
