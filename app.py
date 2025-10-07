from flask import Flask, render_template, request, send_file, redirect, url_for
from datetime import datetime
import io, zipfile

# Word document generation
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

app = Flask(__name__)

# ---------------- Diagnostics ----------------
APP_VERSION = "repo-fresh-1.0.7"

@app.route("/__version")
def __version():
    return APP_VERSION, 200

@app.route("/__health")
def __health():
    return "ok-" + APP_VERSION, 200


# ---------------- Helpers ----------------
def form_to_dict(form):
    """
    Collects form data into a plain dict. If a field has multiple values,
    it collapses to a list; otherwise a string.
    """
    data = {}
    for k in form.keys():
        vals = form.getlist(k)
        data[k] = vals[0] if len(vals) == 1 else vals
    return data


# ---------------- Presales ----------------
@app.route("/", methods=["GET"])
@app.route("/presales", methods=["GET"])
def presales():
    # Provide an empty 'data' so templates referencing it won't 500 on GET
    return render_template("presales_form.html", app_version=APP_VERSION, data={})


@app.route("/presales/submit", methods=["POST"])
def presales_submit():
    data = form_to_dict(request.form)
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template(
        "presales_results.html",
        data=data,
        submitted_at=submitted_at,
        app_version=APP_VERSION,
    )


@app.route("/presales/download", methods=["POST"])
def presales_download():
    """
    Generate a Word (.docx) summary of the Presales questionnaire.
    """
    data = form_to_dict(request.form)

    doc = Document()
    doc.add_heading("Presales Questionnaire Export", 0)
    doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    def add_field(label, key):
        p = doc.add_paragraph()
        r = p.add_run(f"{label}: ")
        r.bold = True
        p.add_run(data.get(key, "") or "—")

    # Sections mirroring the form
    doc.add_heading("Customer & Project", level=1)
    for lbl, key in [
        ("Customer Name", "customer_name"),
        ("Customer Slug", "customer_slug"),
        ("Project Name", "project_name"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Primary Contacts", level=1)
    for lbl, key in [
        ("Primary Contact (Name)", "primary_contact_name"),
        ("Primary Contact (Email)", "primary_contact_email"),
        ("Secondary / Ops Contacts", "secondary_contacts"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Voice of the Customer", level=1)
    doc.add_paragraph(data.get("voc", "") or "—")

    doc.add_heading("Scope", level=1)
    for lbl, key in [
        ("Deployment Scope", "pod_scope"),
        ("Include Test/Dev", "include_test_dev"),
        ("Concurrent Users", "concurrent_users"),
        ("Test/Dev Notes", "test_dev_notes"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Host / Cluster Sizing", level=1)
    for lbl, key in [
        ("ESXi Hosts (per pod)", "host_count"),
        ("CPU per Host", "cpu_per_host"),
        ("RAM per Host", "ram_per_host"),
        ("Other Host Details", "other_host_config"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Storage", level=1)
    for lbl, key in [
        ("Type", "storage_type"),
        ("Vendor", "storage_vendor"),
        ("Model", "storage_model"),
        ("Usable Capacity (TB)", "storage_capacity_tb"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Networking & Load Balancing", level=1)
    for lbl, key in [
        ("Load Balancer", "load_balancer"),
        ("Management Network CIDR", "mgmt_cidr"),
        ("VM / Desktop Networks", "vm_networks"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Access & Identity", level=1)
    for lbl, key in [
        ("3rd-party IdP?", "idp_integrate"),
        ("IdP Provider", "idp_provider"),
    ]:
        add_field(lbl, key)

    doc.add_heading("Additional Notes", level=1)
    doc.add_paragraph(data.get("notes", "") or "—")

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    fname = f"Presales_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=fname,
    )


@app.route("/presales/download-all", methods=["POST"])
def presales_download_all():
    """
    Bundle Presales.docx + SOW.docx + HLD.docx into a single .zip
    using the current Presales form data.
    """
    data = form_to_dict(request.form)
    customer = (data.get("customer_name") or "Customer").replace(" ", "_")
    date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # --- Presales doc ---
    presales_doc = Document()
    presales_doc.add_heading("Presales Questionnaire Export", 0)
    presales_doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    def add_ps(label, key):
        p = presales_doc.add_paragraph()
        r = p.add_run(f"{label}: ")
        r.bold = True
        p.add_run(data.get(key, "") or "—")
    for lbl, key in [
        ("Customer Name", "customer_name"),
        ("Customer Slug", "customer_slug"),
        ("Project Name", "project_name"),
        ("Deployment Scope", "pod_scope"),
        ("Include Test/Dev", "include_test_dev"),
        ("Concurrent Users", "concurrent_users"),
        ("CPU per Host", "cpu_per_host"),
        ("RAM per Host", "ram_per_host"),
        ("Storage Type", "storage_type"),
        ("Load Balancer", "load_balancer"),
        ("3rd-party IdP?", "idp_integrate"),
        ("IdP Provider", "idp_provider"),
    ]:
        add_ps(lbl, key)
    presales_doc.add_heading("Voice of the Customer", level=1)
    presales_doc.add_paragraph(data.get("voc", "") or "—")
    buf_presales = io.BytesIO()
    presales_doc.save(buf_presales)
    buf_presales.seek(0)

    # --- SOW doc (starter content) ---
    sow = Document()
    sow.add_heading(f"Statement of Work (SOW) - {customer}", 0)
    sow.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    sow.add_heading("1. Overview", level=1)
    sow.add_paragraph(
        f"This Statement of Work defines the scope and deliverables for the "
        f"{data.get('project_name','')} engagement with {data.get('customer_name','Customer')}."
    )
    sow.add_heading("2. Scope & Deliverables", level=1)
    sow.add_paragraph(f"Deployment Scope: {data.get('pod_scope','')}")
    sow.add_paragraph(f"Include Test/Dev: {data.get('include_test_dev','')}")
    sow.add_heading("2.1 Business Objectives (Voice of the Customer)", level=2)
    sow.add_paragraph(data.get("voc", "") or "—")
    sow.add_heading("3. Assumptions", level=1)
    sow.add_paragraph("• Required accounts, access, and prerequisites will be available prior to deployment activities.")
    sow.add_paragraph("• Customer stakeholders will be available for timely reviews and approvals.")
    sow.add_heading("4. Roles & Responsibilities", level=1)
    sow.add_paragraph("WWT: Solution design, implementation, validation, knowledge transfer.")
    sow.add_paragraph("Customer: Provide access, change approvals, and operational ownership post-handover.")
    sow.add_heading("5. Milestones", level=1)
    sow.add_paragraph("- Presales Complete\n- Design Approved\n- Deployment\n- Testing/Validation\n- Transition to Operations")
    buf_sow = io.BytesIO()
    sow.save(buf_sow)
    buf_sow.seek(0)

    # --- HLD doc (starter content) ---
    hld = Document()
    hld.add_heading(f"High-Level Design (HLD) - {customer}", 0)
    hld.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    hld.add_heading("1. Executive Summary", level=1)
    hld.add_paragraph(data.get("voc", "") or "—")
    hld.add_heading("2. Logical Architecture", level=1)
    hld.add_paragraph(f"Scope: {data.get('pod_scope','').capitalize()} pod deployment.")
    hld.add_heading("3. Storage & Networking", level=1)
    hld.add_paragraph(f"Storage: {data.get('storage_type','')} {data.get('storage_model','')}")
    hld.add_paragraph(f"Networks: mgmt {data.get('mgmt_cidr','')}, VM networks {data.get('vm_networks','')}")
    hld.add_paragraph(f"Load Balancer: {data.get('load_balancer','')}")
    hld.add_heading("4. Identity & Access", level=1)
    hld.add_paragraph(f"3rd-party IdP: {data.get('idp_integrate','')} ({data.get('idp_provider','')})")
    buf_hld = io.BytesIO()
    hld.save(buf_hld)
    buf_hld.seek(0)

    # --- ZIP bundle ---
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr(f"Presales_{date_str}.docx", buf_presales.getvalue())
        z.writestr(f"SOW_{customer}_{date_str}.docx", buf_sow.getvalue())
        z.writestr(f"HLD_{customer}_{date_str}.docx", buf_hld.getvalue())
    zip_buf.seek(0)
    zip_name = f"Deliverables_{customer}_{date_str}.zip"
    return send_file(zip_buf, mimetype="application/zip", as_attachment=True, download_name=zip_name)


# ---------------- PDG (Pre-Deployment Guide) ----------------
# Schema drives dynamic fields by global vs per-pod scope
# tuple: (section, key, label, type, options, required, applies_to) where applies_to ∈ {"global", "both"}
SCHEMA_PDG = [
    # Global / Admin
    ("Global", "project_name", "Project Name", "text", "", True, "global"),
    ("Global", "customer_name", "Customer Name", "text", "", True, "global"),
    ("Global", "primary_contact", "Primary Technical Contact (name/email)", "text", "", True, "global"),
    ("Global", "support_contacts", "Operations / Support Contacts", "text", "", False, "global"),
    ("Global", "change_window", "Change Window / Maintenance Policy", "text", "", False, "global"),
    ("Global", "certificates_owner", "Certificates Owner (who renews/manages)", "text", "", True, "global"),
    ("Global", "ntp_servers", "NTP Servers", "text", "", True, "global"),
    ("Global", "dns_servers", "DNS Servers", "text", "", True, "global"),
    ("Global", "dns_zones", "DNS Zones/Suffixes", "text", "", False, "global"),
    ("Global", "idp_integration", "3rd-Party IdP Integration", "select", "None|Entra ID|Okta|Ping|ADFS|Other", True, "global"),
    ("Global", "idp_provider_notes", "IdP Notes (If Other)", "text", "", False, "global"),

    # Networking (per pod)
    ("Networking", "mgmt_cidr", "Management Network CIDR", "text", "", True, "both"),
    ("Networking", "vmotion_cidr", "vMotion Network CIDR", "text", "", False, "both"),
    ("Networking", "vm_networks", "VM Networks (desktop pools, infra)", "text", "", True, "both"),
    ("Networking", "vsan_storage_cidr", "vSAN/Storage Network CIDR", "text", "", False, "both"),
    ("Networking", "dmz_uag_cidr", "DMZ / UAG Network CIDR", "text", "", False, "both"),
    ("Networking", "vip_ranges", "VIP IPs / Ranges reserved", "text", "", False, "both"),
    ("Networking", "vlans", "VLAN IDs (mgmt, vMotion, vSAN/Storage, UAG DMZ)", "text", "", True, "both"),
    ("Networking", "firewall_zones", "Firewall Zones and Inter-site Rules", "text", "", False, "both"),

    # Compute / Storage (per pod)
    ("Compute/Storage", "host_count", "ESXi Hosts (count per pod)", "text", "", True, "both"),
    ("Compute/Storage", "cpu_per_host", "CPU per Host", "text", "", True, "both"),
    ("Compute/Storage", "ram_per_host", "RAM per Host", "text", "", True, "both"),
    ("Compute/Storage", "storage_type", "Primary Storage Type", "select", "vSAN|Pure Storage|PowerScale|Other", True, "both"),
    ("Compute/Storage", "storage_model", "Storage Model (if external array)", "text", "", False, "both"),
    ("Compute/Storage", "storage_capacity_tb", "Usable Capacity (TB)", "text", "", False, "both"),

    # Load Balancing (per pod)
    ("Load Balancing", "load_balancer", "Load Balancer Platform", "select", "F5 BIG-IP|Avi / NSX ALB|Netscaler (Citrix ADC)|Other|None", True, "both"),
    ("Load Balancing", "lb_partitions", "LB Partitions / Tenants", "text", "", False, "both"),
    ("Load Balancing", "health_monitors", "Health Monitors (types/intervals)", "text", "", False, "both"),

    # Horizon Core (per pod)
    ("Horizon", "uag_count", "UAG Count", "text", "", True, "both"),
    ("Horizon", "cs_count", "Connection Server Count", "text", "", True, "both"),
    ("Horizon", "admin_console_url", "Horizon Admin URL", "text", "", False, "both"),
    ("Horizon", "uag_external_url", "UAG External URL (per site)", "text", "", False, "both"),
    ("Horizon", "uag_internal_url", "UAG Internal URL (per site)", "text", "", False, "both"),
    ("Horizon", "dem_configshare", "DEM Config Share (path)", "text", "", False, "both"),
    ("Horizon", "fslogix_profile", "FSLogix Profile Path/Provider", "text", "", False, "both"),
    ("Horizon", "appvols_manager_url", "App Volumes Manager URL", "text", "", False, "both"),

    # Certificates (global)
    ("Certificates", "wildcard_fqdn", "Wildcard/SAN FQDNs", "text", "", True, "global"),
    ("Certificates", "sni_requirements", "SNI Requirements", "text", "", False, "global"),
    ("Certificates", "pkcs12_escrow", "PKCS#12 Escrowed?", "select", "Yes|No|Planned", True, "global"),

    # Ops (global)
    ("Ops", "monitoring_tools", "Monitoring/Logging Tools", "text", "", False, "global"),
    ("Ops", "backup_targets", "Backup/Recovery Targets", "text", "", False, "global"),
]

def pdg_groups(is_multi):
    """Split schema into global and per-pod lists."""
    g = [x for x in SCHEMA_PDG if x[6] == "global"]
    pod = [x for x in SCHEMA_PDG if x[6] == "both"]
    return g, pod, (pod if is_multi else [])


@app.route("/predeploy", methods=["GET"])
def predeploy_redirect():
    return redirect(url_for("pdg_scope"))


@app.route("/pdg", methods=["GET"])
def pdg_scope():
    return render_template("pdg_scope.html", app_version=APP_VERSION)


@app.route("/pdg/form", methods=["POST"])
def pdg_form():
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    g_items, pod1_items, pod2_items = pdg_groups(is_multi)
    return render_template(
        "pdg_form.html",
        is_multi=is_multi,
        g_items=g_items,
        pod1_items=pod1_items,
        pod2_items=pod2_items,
        app_version=APP_VERSION,
    )


@app.route("/pdg/submit", methods=["POST"])
def pdg_submit():
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    data = {k: request.form.get(k, "") for k in request.form.keys()}
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template(
        "pdg_results.html",
        data=data,
        is_multi=is_multi,
        submitted_at=submitted_at,
        app_version=APP_VERSION,
    )


@app.route("/pdg/download-docx", methods=["POST"])
def pdg_download_docx():
    """
    Export PDG responses to a Word document.
    """
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    data = {k: request.form.get(k, "") for k in request.form.keys()}

    doc = Document()
    title = doc.add_heading("Pre-Deployment Guide (PDG)", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    doc.add_paragraph(f"Scope: {'Multi-pod' if is_multi else 'Single pod'}")

    def write_group(heading, items, prefix):
        doc.add_heading(heading, level=1)
        current = None
        for (section, key, label, type_, options, required, applies_to) in items:
            if current != section:
                current = section
                doc.add_heading(section, level=2)
            val = data.get(f"{prefix}_{key}", "")
            p = doc.add_paragraph()
            r = p.add_run(f"{label}: ")
            r.bold = True
            p.add_run(val if val else "—")

    g_items, pod1_items, pod2_items = pdg_groups(is_multi)
    write_group("Global", g_items, "global")
    write_group("Pod 1", pod1_items, "pod1")
    if is_multi:
        write_group("Pod 2", pod2_items, "pod2")
        # GSLB block for multi-pod
        doc.add_heading("GSLB (Multi-Pod)", level=1)
        for label, key in [
            ("Enable GSLB?", "gslb_enable"),
            ("GSLB FQDN(s) (Internal/External URLs)", "gslb_fqdns"),
            ("GTM configuration (data centers, pools, monitors)", "gslb_gtm"),
            ("LTM VIPs per site (UAG, CS, Admin, App Volumes, DEM)", "gslb_ltm_vips"),
            ("Health monitors (types, intervals, response codes)", "gslb_monitors"),
            ("Failover/steering policy (round-robin, topology, latency, geo)", "gslb_policy"),
            ("Certificates & SNI (SANs/wildcards, renewal ownership)", "gslb_certs"),
        ]:
            p = doc.add_paragraph()
            r = p.add_run(f"{label}: ")
            r.bold = True
            p.add_run(data.get(key, "") or "—")

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    fname = f"PDG_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=fname,
    )


# ---------------- Main ----------------
if __name__ == "__main__":
    # Debug True for local; Render uses gunicorn Procfile in production
    app.run(host="0.0.0.0", port=5000, debug=True)
