from flask import request, render_template, redirect, url_for, flash
from . import presales_bp

@presales_bp.route("/presales/new", methods=["GET", "POST"])
def presales_new():
    if request.method == "POST":
        # TODO: persist somewhere real (db, GitHub, etc.)
        data = request.form.to_dict(flat=True)
        # Basic guardrails
        required = ["company_name", "customer_name", "concurrent_users", "host_cpu_cores", "host_ram_gb", "vm_vcpu", "vm_ram_gb"]
        missing = [r for r in required if not data.get(r)]
        if missing:
            flash(f"Missing required fields: {', '.join(missing)}", "error")
            return render_template("presales/form.html")

        flash("Presales discovery saved (in-memory placeholder). Wire to your storage next.", "success")
        return redirect(url_for("presales.presales_new"))
    return render_template("presales/form.html")
