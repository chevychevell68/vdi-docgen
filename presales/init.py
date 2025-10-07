from flask import Blueprint
presales_bp = Blueprint("presales", __name__, template_folder="templates", static_folder="static")
from . import routes  # noqa
