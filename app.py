
from flask import Flask, render_template, request, send_file, redirect, url_for
from datetime import datetime
import io

app = Flask(__name__)

# ---------------- Shared helpers ----------------
def form_to_dict(form):
    data = {}
    for k in form.keys():
        vals = form.getlist(k)
        data[k] = vals[0] if len(vals) == 1 else vals
    return data

# ---------------- PDG schema (approximation aligned to pod deployments) ----------------
# tuple: (section, key, label, type, options, required, applies_to) where applies_to in {"global","both"}
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
    g = [x for x in SCHEMA_PDG if x[6] == "global"]
    pod = [x for x in SCHEMA_PDG if x[6] == "both"]
    return g, pod, (pod if is_multi else [])

# ---------------- Routes ----------------

# Root = Presales (explicit)
@app.route("/", methods=["GET"])
@app.route("/presales", methods=["GET"])
def presales():
    return render_template("presales_form.html")

@app.route("/presales/submit", methods=["POST"])
def presales_submit():
    data = form_to_dict(request.form)
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template("presales_results.html", data=data, submitted_at=submitted_at)

@app.route("/presales/download", methods=["POST"])
def presales_download():
    data = form_to_dict(request.form)
    md = render_template("presales_export.md", data=data, now=datetime.utcnow())
    buf = io.BytesIO(md.encode("utf-8"))
    fname = f"presales_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    return send_file(buf, mimetype="text/markdown", as_attachment=True, download_name=fname)

# Pre-Deploy = PDG
@app.route("/predeploy", methods=["GET"])
def predeploy_redirect():
    return redirect(url_for("pdg_scope"))

@app.route("/pdg", methods=["GET"])
def pdg_scope():
    return render_template("pdg_scope.html")

@app.route("/pdg/form", methods=["POST"])
def pdg_form():
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    g_items, pod1_items, pod2_items = pdg_groups(is_multi)
    return render_template("pdg_form.html",
                           is_multi=is_multi,
                           g_items=g_items,
                           pod1_items=pod1_items,
                           pod2_items=pod2_items)

@app.route("/pdg/submit", methods=["POST"])
def pdg_submit():
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    data = {k: request.form.get(k, "") for k in request.form.keys()}
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template("pdg_results.html", data=data, is_multi=is_multi, submitted_at=submitted_at)

@app.route("/pdg/download-docx", methods=["POST"])
def pdg_download_docx():
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    data = {k: request.form.get(k, "") for k in request.form.keys()}

    doc = Document()
    title = doc.add_heading("Pre-Deployment Guide (PDG)", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    doc.add_paragraph(f"Scope: {'Multi-pod' if is_multi else 'Single pod'}")

    # helper to write a group
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
        # GSLB block
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
    return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     as_attachment=True, download_name=fname)

# ---------------- main ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
