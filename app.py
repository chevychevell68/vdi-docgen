
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import io, csv, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev"  # for flash messages

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

@app.route("/manage-fields", methods=["GET"])
def manage_fields():
    # Show current CSV presence and provide upload form
    exists = os.path.exists(FIELDS_CSV_PATH)
    size = os.path.getsize(FIELDS_CSV_PATH) if exists else 0
    return render_template("manage_fields.html", exists=exists, size=size)

@app.route("/manage-fields/upload", methods=["POST"])
def manage_fields_upload():
    file = request.files.get("fields_csv")
    if not file or file.filename == "":
        flash("Please choose a CSV file.", "warning")
        return redirect(url_for("manage_fields"))
    filename = file.filename.lower()
    if not filename.endswith(".csv"):
        flash("Only .csv files are supported.", "warning")
        return redirect(url_for("manage_fields"))
    try:
        file.save(FIELDS_CSV_PATH)
        flash("Fields CSV uploaded successfully.", "success")
    except Exception as e:
        flash(f"Upload failed: {e}", "danger")
    return redirect(url_for("manage_fields"))

@app.route("/presales", methods=["GET"])
def presales():
    # Explicit route for the presales questionnaire
    return render_template("form.html")

@app.route("/predeploy", methods=["GET"])
def predeploy():
    # Entry page for Pre-Deployment checklist builder (scope-only preview)
    return render_template("predeploy.html")

@app.route("/predeploy/build", methods=["POST"])
def predeploy_build():
    # Build checklist using only the selected pod scope (single/multi)
    pod_scope = request.form.get("pod_scope", "single")
    is_multi = (pod_scope == "multi")
    fields = load_fields_from_csv()
    data = {"pod_scope": pod_scope}  # minimal context for rendering
    return render_template("checklist.html", data=data, fields=fields, is_multi=is_multi, now=datetime.utcnow())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
