from flask import request, render_template, redirect, url_for, flash
from . import presales_bp

@presales_bp.route("/presales/new", methods=["GET", "POST"])
def presales_new():
    if request.method == "POST":
        _data = request.form.to_dict(flat=True)
        flash("Presales discovery saved (in-memory placeholder). Wire to your storage next.", "success")
        return redirect(url_for("presales.presales_new"))
    return render_template("presales_form.html", form=request.form)
