import os
from flask import Flask, request, render_template, redirect, url_for, flash

app = Flask(__name__, template_folder="templates", static_folder="static")

# Use your existing secret key if you have one; this enables flash messages.
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

@app.route("/")
def index():
    # Simple landing; link to the new presales form.
    return render_template("index.html") if template_exists("index.html") else (
        '<!doctype html><html><head><meta charset="utf-8"><title>App</title></head>'
        '<body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial">'
        '<h1>App is running</h1>'
        '<p><a href="/presales/new">Open Horizon Presales Discovery form</a></p>'
        "</body></html>"
    )

@app.route("/presales/new", methods=["GET", "POST"])
def presales_new():
    """
    Architect-led Horizon presales discovery form.
    Renders templates/presales_form.html (you’ve already put this in your global templates dir).
    """
    if request.method == "POST":
        data = request.form.to_dict(flat=True)

        # Minimal required fields to avoid empty submissions
        required = [
            "company_name", "customer_name",
            "concurrent_users",
            "host_cpu_cores", "host_ram_gb",
            "vm_vcpu", "vm_ram_gb",
        ]
        missing = [r for r in required if not (data.get(r) or "").strip()]
        if missing:
            flash(f"Missing required fields: {', '.join(missing)}", "error")
            return render_template("presales_form.html", form=data)

        # TODO: Persist somewhere real (DB, GitHub commit, JSON file, etc.)
        # For now we just echo back a success flash and reload the form.
        flash("Presales discovery saved (placeholder). Wire persistence next.", "success")
        return redirect(url_for("presales_new"))

    # GET
    return render_template("presales_form.html")

# ---------- Helpers & error handlers ----------

def template_exists(name: str) -> bool:
    """
    Lightweight check so the app runs even if you don't have index.html.
    """
    try:
        # Will raise TemplateNotFound if missing
        app.jinja_env.get_or_select_template(name)
        return True
    except Exception:
        return False

@app.errorhandler(404)
def not_found(e):
    return (
        render_template("404.html"),
        404,
    ) if template_exists("404.html") else ("Not Found", 404)

@app.errorhandler(500)
def server_error(e):
    return (
        render_template("500.html"),
        500,
    ) if template_exists("500.html") else ("Internal Server Error", 500)

# ---------- Local dev entrypoint ----------

if __name__ == "__main__":
    # Bind to 0.0.0.0 for container/Render-style runs; change as needed.
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "1") == "1")
