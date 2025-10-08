## [v1.1.2] – Added Placeholder Text
### Added
- Auto-injected sample placeholder text for all presales form fields (via centralized logic in `base.html`).
- Example hints now appear dynamically (e.g., “e.g., 250”, “https://your-instance.example.com/...”) without modifying each individual field template.

### Fixed / Improved
- No UI regressions; all required field asterisks remain intact.
- Dropdowns now display a default “Select…” option for better UX.

### Deployment
- Commit: `v1.1.2`
- Branch: `v1.1.1`
- Service: Render (deploying from `v1.1.1`)
