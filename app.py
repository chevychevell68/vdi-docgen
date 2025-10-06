import io, zipfile, os, yaml
from flask import Flask, render_template, request, send_file, abort
from jinja2 import Environment, FileSystemLoader, StrictUndefined

app = Flask(__name__)

TEMPLATES_DIR = "templates"
DOC_TEMPLATES = [
    ("sow.md.j2", "SOW.md"),
    ("hld.md.j2", "HLD.md"),
    ("lld.md.j2", "LLD.md"),
    ("pdg.md.j2", "PDG.md"),
    ("asbuilt.md.j2", "AsBuilt.md"),
]

def render_docs(data: dict) -> dict:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    files = {}
    # simple validation
    for sec, key in [("customer","name"),("horizon","version"),("horizon","pods"),("engagement","phases")]:
        if not (sec in data and key in data[sec] and data[sec][key]):
            raise ValueError(f"Missing required field: {sec}.{key}")

    for tpl, outname in DOC_TEMPLATES:
        tpl_obj = env.get_template(tpl)
        files[outname] = tpl_obj.render(**data)
    return files

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        # Option A: YAML upload
        if "intake_yaml" in request.files and request.files["intake_yaml"].filename:
            data = yaml.safe_load(request.files["intake_yaml"].read().decode("utf-8"))
        else:
            # Option B: quick form (minimal fields)
            customer = request.form.get("customer_name","").strip()
            horizon_version = request.form.get("horizon_version","2503.1").strip()
            pods_count = int(request.form.get("pods_count","1"))
            uag_internet = (request.form.get("uag_internet","no") == "yes")
            pods = []
            for i in range(pods_count):
                pods.append({
                    "name": f"Pod {i+1}",
                    "site": request.form.get(f"pod{i+1}_site","DC1"),
                    "region": request.form.get(f"pod{i+1}_region","Central US"),
                    "vcenter": request.form.get(f"pod{i+1}_vcenter","vcsa01.local"),
                    "uag": {"internet_facing": uag_internet, "count": 2},
                })

            data = {
                "customer": {"name": customer or "Customer"},
                "engagement": {
                    "version": request.form.get("version","1.0.0"),
                    "changes": [],
                    "phases": [
                        {"name":"Assessment & HLD","billing_milestone":"30%"},
                        {"name":"Build & LLD","billing_milestone":"40%"},
                        {"name":"Pilot & PDG","billing_milestone":"20%"},
                        {"name":"As-Built & Handover","billing_milestone":"10%"},
                    ],
                    "timeline": {
                        "start_date": request.form.get("start_date",""),
                        "notes": request.form.get("timeline_notes","")
                    }
                },
                "horizon": {
                    "version": horizon_version,
                    "cpa_enabled": (pods_count > 1),
                    "pods": pods
                },
                "image_mgmt": {
                    "os": request.form.get("os","Windows 11 23H2"),
                    "instant_clone": True,
                    "dem": True,
                    "fslogix": {"enabled": True, "cloud_cache": True, "capacity_target":"SMB"}
                },
                "security": {
                    "mfa": request.form.get("mfa","Duo"),
                    "certs_managed_by": request.form.get("certs_owner","PKI team"),
                    "external_exposure_in_poc": (request.form.get("poc_external","no")=="yes")
                },
                "constraints": {
                    "assumptions": ["DNS/NTP/routing provided by customer"],
                    "out_of_scope": ["Internet-facing UAGs in POC"] if request.form.get("poc_external","no")!="yes" else []
                },
                "deliverable_options": {
                    "include_architecture_diagrams": True,
                    "include_risk_register": True,
                    "include_runbooks": True
                }
            }

        files = render_docs(data)

        # stream a ZIP back to the browser
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            # include the resolved intake for audit
            z.writestr("intake.resolved.yaml", yaml.safe_dump(data, sort_keys=False))
            for name, content in files.items():
                z.writestr(name, content)
        mem.seek(0)
        return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="deliverables.zip")
    except Exception as e:
        return abort(400, str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
