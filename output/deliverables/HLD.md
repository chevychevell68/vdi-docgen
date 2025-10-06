# High-Level Design — NewCo

## Overview
Horizon 2503.1 across 2 pods; CPA enabled. External exposure in POC: Yes.

## Architecture Summary
### Pod 1 (DC1 / Central US)
- UAG: internet-facing × 2
- vCenter: vcsa01.newco.com
### Pod 2 (DC2 / US East 2)
- UAG: internet-facing × 2
- vCenter: vcsa02.newco.com

## Image & Persona
- OS: Windows 11 23H2, Instant Clone: Yes
- DEM: Enabled
- FSLogix: Enabled, Cloud Cache: Yes, Capacity Target: SMB
## Security
- MFA: Azure Identity
- Certificates managed by: PKI team

## Risks (Initial)
- Misaligned UAG exposure expectations between POC and Prod.
- Image management drift without governance.
