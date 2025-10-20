from flask import Blueprint

presales_bp = Blueprint("presales", __name__, template_folder="templates", static_folder="static", url_prefix="/presales")

from . import routes  # noqa: E402,F401
