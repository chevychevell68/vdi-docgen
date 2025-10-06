
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import io, csv, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev"

# ---------------- PDG: Static schema (no CSV) ----------------
# Each tuple: (section, key, label, type, options, required, applies_to)
# applies_to: global | pod1 | pod2 | both
SCHEMA_PDG = [
    # Global / Administrative
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

def build_pdg_groups(is_multi):
    global_items = [x for x in SCHEMA_PDG if x[6] == "global"]
    pod_items = [x for x in SCHEMA_PDG if x[6] in ("both", "pod1")]
    pod2_items = [x for x in SCHEMA_PDG if x[6] in ("both", "pod2")] if is_multi else []
    return global_items, pod_items, pod2_items
  # for flash messages

FIELDS_CSV_PATH = os.path.join(os.path.dirname(__file__), "fields.csv")

def form_to_dict(form):
    data = {}
    for k in form.keys():
        vals = form.getlist(k)
        data[k] = vals[0] if len(vals) == 1 else vals
    return data

def load_fields_from_csv():
    fields = []
    if os.path.exists(FIELDS_CSV_PATH):
        with open(FIELDS_CSV_PATH, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
                row.setdefault("section", "General")
                row.setdefault("field_key", "")
                row.setdefault("label", row.get("field_key", ""))
                row.setdefault("type", "text")
                row.setdefault("options", "")
                row.setdefault("required", "no")
                row.setdefault("applies_to", "both")  # pod1, pod2, both, global
                fields.append(row)
    return fields

@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = form_to_dict(request.form)
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template("results.html", data=data, submitted_at=submitted_at)

@app.route("/download", methods=["POST"])
def download():
    data = form_to_dict(request.form)
    md = render_template("questionnaire.md", data=data, now=datetime.utcnow())
    buf = io.BytesIO(md.encode("utf-8"))
    filename = "presales_questionnaire_{dt}.md".format(dt=datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    return send_file(buf, mimetype="text/markdown", as_attachment=True, download_name=filename)

@app.route("/checklist", methods=["POST"])
def checklist():
    # Generate the Pre-Deployment Checklist HTML view from the submission + CSV fields.
    data = form_to_dict(request.form)
    fields = load_fields_from_csv()
    pod_scope = data.get("pod_scope", "single")
    is_multi = pod_scope == "multi"

    return render_template(
        "checklist.html",
        data=data,
        fields=fields,
        is_multi=is_multi,
        now=datetime.utcnow()
    )

@app.route("/checklist/download", methods=["POST"])
def checklist_download():
    # Render the checklist to Markdown for export.
    data = form_to_dict(request.form)
    fields = load_fields_from_csv()
    pod_scope = data.get("pod_scope", "single")
    is_multi = pod_scope == "multi"

    md = render_template("checklist.md", data=data, fields=fields, is_multi=is_multi, now=datetime.utcnow())
    buf = io.BytesIO(md.encode("utf-8"))
    filename = "predeployment_checklist_{dt}.md".format(dt=datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    return send_file(buf, mimetype="text/markdown", as_attachment=True, download_name=filename)

from flask import abort

@app.route("/manage-fields", methods=["GET"])
def manage_fields():
    abort(404)

@app.route("/manage-fields/upload", methods=["POST"])
def manage_fields_upload():
    abort(404)

@app.route("/presales", methods=["GET"])
def presales():
    # Explicit route for the presales questionnaire
    return render_template("form.html")

@app.route("/predeploy", methods=["GET"])
def predeploy():
    return redirect(url_for("pdg"))

@app.route("/predeploy/build", methods=["POST"])
def predeploy_build():
    # Build checklist using only the selected pod scope (single/multi)
    pod_scope = request.form.get("pod_scope", "single")
    is_multi = (pod_scope == "multi")
    fields = load_fields_from_csv()
    data = {"pod_scope": pod_scope}  # minimal context for rendering
    return render_template("checklist.html", data=data, fields=fields, is_multi=is_multi, now=datetime.utcnow())


@app.route("/pdg", methods=["GET"])
def pdg():
    # Scope selector for PDG standalone mode
    return render_template("pdg_scope.html")

@app.route("/pdg/form", methods=["POST"])
def pdg_form():
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    g_items, pod1_items, pod2_items = build_pdg_groups(is_multi)
    return render_template("pdg_form.html",
                           is_multi=is_multi,
                           g_items=g_items,
                           pod1_items=pod1_items,
                           pod2_items=pod2_items)

@app.route("/pdg/submit", methods=["POST"])
def pdg_submit():
    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    # Capture all fields generically
    data = {k: request.form.get(k, "") for k in request.form.keys()}
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template("pdg_results.html", data=data, is_multi=is_multi, submitted_at=submitted_at)

@app.route("/pdg/download-docx", methods=["POST"])
def pdg_download_docx():
    # Generate a Word document from the PDG submission
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    scope = request.form.get("pod_scope", "single")
    is_multi = (scope == "multi")
    data = {k: request.form.get(k, "") for k in request.form.keys()}

    doc = Document()
    title = doc.add_heading("Pre-Deployment Guide (PDG)", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    doc.add_paragraph(f"Scope: {'Multi-pod' if is_multi else 'Single pod'}")

    def add_section(h, items, prefix):
        doc.add_heading(h, level=1)
        current_group = None
        for (section, key, label, type_, options, required, applies_to) in items:
            if current_group != section:
                current_group = section
                doc.add_heading(section, level=2)
            val = data.get(f"{prefix}_{key}", "")
            p = doc.add_paragraph()
            run = p.add_run(f"{label}: ")
            run.bold = True
            p.add_run(val if val else "—")

    # Global
    g_items, pod1_items, pod2_items = build_pdg_groups(is_multi)
    add_section("Global", g_items, "global")

    # Pod 1
    add_section("Pod 1", pod1_items, "pod1")

    # Pod 2 + GSLB if multi
    if is_multi:
        add_section("Pod 2", pod2_items, "pod2")
        doc.add_heading("GSLB (Multi-Pod)", level=1)
        gslb_fields = [
            ("Enable GSLB?", data.get("gslb_enable", "")),
            ("GSLB FQDN(s) (Internal/External URLs)", data.get("gslb_fqdns", "")),
            ("GTM configuration (data centers, pools, monitors)", data.get("gslb_gtm", "")),
            ("LTM VIPs per site (UAG, CS, Admin, App Volumes, DEM)", data.get("gslb_ltm_vips", "")),
            ("Health monitors (types, intervals, response codes)", data.get("gslb_monitors", "")),
            ("Failover/steering policy (round-robin, topology, latency, geo)", data.get("gslb_policy", "")),
            ("Certificates & SNI (SANs/wildcards, renewal ownership)", data.get("gslb_certs", "")),
        ]
        for label, val in gslb_fields:
            p = doc.add_paragraph()
            run = p.add_run(f"{label}: ")
            run.bold = True
            p.add_run(val if val else "—")

    import io
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = "PDG_{dt}.docx".format(dt=datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
