
from flask import Flask, render_template, request, send_file, redirect, url_for
import io
from datetime import datetime

app = Flask(__name__)

# Utility: convert form MultiDict to plain dict with lists flattened
def form_to_dict(form):
    data = {}
    for k in form.keys():
        vals = form.getlist(k)
        if len(vals) == 1:
            data[k] = vals[0]
        else:
            data[k] = vals
    return data

@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = form_to_dict(request.form)
    # Create a lightweight summary to show on results page
    submitted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return render_template("results.html", data=data, submitted_at=submitted_at)

@app.route("/download", methods=["POST"])
def download():
    # Receive posted data as the same form payload and render markdown
    data = form_to_dict(request.form)
    md = render_template("questionnaire.md", data=data, now=datetime.utcnow())
    buf = io.BytesIO(md.encode("utf-8"))
    filename = "presales_questionnaire_{dt}.md".format(dt=datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
    return send_file(buf, mimetype="text/markdown", as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
