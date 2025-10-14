
def _to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

def _to_int(v, default=0):
    try:
        return int(str(v).replace(",", "").strip())
    except Exception:
        return default

def build_context(form: dict) -> dict:
    ctx = {
        "project": {
            "name": form.get("project_name", ""),
            "customer": form.get("customer_name", ""),
            "voice_of_customer": form.get("voc", ""),
            "maintenance_window": form.get("maint_window", ""),
            "cab": {
                "required": _to_bool(form.get("cab_required", "false")),
                "start": form.get("cab_start", ""),
                "end": form.get("cab_end", ""),
            },
        },
        "horizon": {
            "components": {
                "connection_servers": _to_int(form.get("cs_count", "3")),
                "replicas": _to_int(form.get("cs_replicas", "2")),
                "uag": _to_int(form.get("uag_count", "3")),
                "enrollment_servers": _to_int(form.get("enroll_count", "2")),
                "appvol_managers": _to_int(form.get("av_mgr_count", "3")),
            },
            "features": {
                "instant_clone": _to_bool(form.get("instant_clone", "true")),
                "fslogix": _to_bool(form.get("fslogix", "true")),
                "dem": _to_bool(form.get("dem", "true")),
            },
        },
        "identity": {
            "ad_domain": form.get("ad_domain", ""),
            "truesso": _to_bool(form.get("truesso_enabled", "true")),
            "external_idp": {
                "enabled": _to_bool(form.get("ext_idp_enabled", "false")),
                "provider": form.get("ext_idp_provider", ""),
            },
        },
        "storage": {
            "type": form.get("storage_type", "vsan"),
            "policy": form.get("vsan_policy", "vdi-default"),
        },
        "networking": {
            "f5": _to_bool(form.get("f5_present", "true")),
            "subnets": form.get("subnets_csv", ""),
        },
        "security": {
            "cert_source": form.get("cert_source", "customer"),
            "logging": form.get("logging_target", ""),
        },
        "users": {
            "total": _to_int(form.get("user_count", "0")),
            "region_mix": {
                "continental_us_pct": _to_int(form.get("continental_us_pct", "100")),
                "emea_pct": _to_int(form.get("emea_pct", "0")),
                "apac_pct": _to_int(form.get("apac_pct", "0")),
                "latam_pct": _to_int(form.get("latam_pct", "0")),
            },
        },
        "endpoints": {
            "contractor_partner_access": _to_bool(form.get("partner_laptop_access", "false")),
        },
        "deliverables": {
            # Safe defaults: if form doesn't have checkboxes yet, generate all
            "sow": _to_bool(form.get("deliverable_sow", "true")),
            "hld": _to_bool(form.get("deliverable_hld", "true")),
            "lld": _to_bool(form.get("deliverable_lld", "true")),
            "runbook": _to_bool(form.get("deliverable_runbook", "true")),
            "pdg": _to_bool(form.get("deliverable_pdg", "true")),
            "loe_wbs": _to_bool(form.get("deliverable_loe_wbs", "true")),
            "atp": _to_bool(form.get("deliverable_atp", "true")),
            "adoption_plan": _to_bool(form.get("deliverable_adoption_plan", "true")),
        },
        "assumptions": form.get("assumptions", ""),
        "out_of_scope": form.get("out_of_scope", ""),
        "risks": form.get("risks", ""),
        "constraints": form.get("constraints", ""),
        "timeline": form.get("timeline_notes", ""),
    }

    total = max(1, ctx["users"]["total"])
    mix = ctx["users"]["region_mix"]
    ctx["users"]["by_region"] = {
        "continental_us": round(total * mix["continental_us_pct"] / 100),
        "emea": round(total * mix["emea_pct"] / 100),
        "apac": round(total * mix["apac_pct"] / 100),
        "latam": round(total * mix["latam_pct"] / 100),
    }
    return ctx
