from flask import request, render_template, redirect, url_for, flash
from . import presales_bp  # presales_bp = Blueprint("presales", __name__, url_prefix="/presales")

@presales_bp.route("/", methods=["GET", "POST"], strict_slashes=False)
def presales_new():
    if request.method == "POST":
        _data = request.form.to_dict(flat=True)
        # TODO: persist _data to your storage
        flash("Presales discovery saved (in-memory placeholder). Wire to your storage next.", "success")
        return redirect(url_for("presales.presales_new"))

    # GET render: pass an empty dict so Jinja checks don't error on None
    return render_template("presales_form.html", form={})
