from flask import Flask, render_template, request, send_file, redirect, url_for
from datetime import datetime
import io, zipfile
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

app = Flask(__name__)
APP_VERSION = "repo-fresh-1.0.7"

@app.route("/__version")
def __version():
    return APP_VERSION, 200

def form_to_dict(form):
    data = {}
    for k in form.keys():
        vals = form.getlist(k)
        data[k] = vals[0] if len(vals) == 1 else vals
    return data

@app.route("/", methods=["GET"])
@app.route("/presales", methods=["GET"])
def presales():
    return render_template("presales_form.html", app_version=APP_VERSION, data={})

@app.route("/presales/submit", methods=["POST"])
def presales_submit():
    data = form_to_dict(request.form)
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template("presales_results.html", data=data, submitted_at=submitted_at, app_version=APP_VERSION)

# Existing single-docx export
@app.route("/presales/download", methods=["POST"])
def presales_download():
    data = form_to_dict(request.form)
    doc = Document()
    doc.add_heading("Presales Questionnaire Export", 0)
    doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    for k, v in data.items():
        p = doc.add_paragraph()
        r = p.add_run(f"{k.replace('_', ' ').title()}: ")
        r.bold = True
        p.add_run(str(v))
    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    fname = f"Presales_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
    return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     as_attachment=True, download_name=fname)

# New ZIP export with SOW + HLD
@app.route("/presales/download-all", methods=["POST"])
def presales_download_all():
    data = form_to_dict(request.form)
    customer = data.get("customer_name", "Customer").replace(" ", "_")
    date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # --- Build Presales doc ---
    presales_doc = Document()
    presales_doc.add_heading("Presales Questionnaire Export", 0)
    presales_doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    for k, v in data.items():
        p = presales_doc.add_paragraph()
        r = p.add_run(f"{k.replace('_', ' ').title()}: ")
        r.bold = True
        p.add_run(str(v))
    presales_buf = io.BytesIO()
    presales_doc.save(presales_buf)
    presales_buf.seek(0)

    # --- Build SOW doc ---
    sow = Document()
    sow.add_heading(f"Statement of Work (SOW) - {customer}", 0)
    sow.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    sow.add_heading("1. Overview", level=1)
    sow.add_paragraph(f"This Statement of Work defines the scope and deliverables for the "
                      f"{data.get('project_name','')} engagement with {customer}.")
    sow.add_heading("2. Scope & Deliverables", level=1)
    sow.add_paragraph(f"Deployment Scope: {data.get('pod_scope','')}")
    sow.add_paragraph(f"Include Test/Dev: {data.get('include_test_dev','')}")
    sow.add_paragraph(f"Voice of the Customer: {data.get('voc','')}")
    sow.add_heading("3. Assumptions", level=1)
    sow.add_paragraph("All infrastructure prerequisites, accounts, and access will be in place before deployment activities begin.")
    sow.add_heading("4. Roles & Responsibilities", level=1)
    sow.add_paragraph("WWT: Solution design, implementation, and validation.\nCustomer: Provide access, review, and approvals.")
    sow.add_heading("5. Milestones", level=1)
    sow.add_paragraph("- Presales Complete\n- Design Approved\n- Deployment\n- Testing\n- Transition to Operations")
    sow_buf = io.BytesIO()
    sow.save(sow_buf)
    sow_buf.seek(0)

    # --- Build HLD doc ---
    hld = Document()
    hld.add_heading(f"High-Level Design (HLD) - {customer}", 0)
    hld.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    hld.add_heading("1. Executive Summary", level=1)
    hld.add_paragraph(data.get("voc", ""))
    hld.add_heading("2. Logical Architecture", level=1)
    hld.add_paragraph(f"Scope: {data.get('pod_scope','')} pod deployment.")
    hld.add_heading("3. Storage & Networking", level=1)
    hld.add_paragraph(f"Storage: {data.get('storage_type','')} {data.get('storage_model','')}")
    hld.add_paragraph(f"Load Balancer: {data.get('load_balancer','')}")
    hld.add_heading("4. Identity & Access", level=1)
    hld.add_paragraph(f"3rd-party IdP: {data.get('idp_integrate','')} ({data.get('idp_provider','')})")
    hld_buf = io.BytesIO()
    hld.save(hld_buf)
    hld_buf.seek(0)

    # --- ZIP bundle ---
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr(f"Presales_{date_str}.docx", presales_buf.getvalue())
        z.writestr(f"SOW_{customer}_{date_str}.docx", sow_buf.getvalue())
        z.writestr(f"HLD_{customer}_{date_str}.docx", hld_buf.getvalue())
    zip_buf.seek(0)
    zip_name = f"Deliverables_{customer}_{date_str}.zip"
    return send_file(zip_buf, mimetype="application/zip", as_attachment=True, download_name=zip_name)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
