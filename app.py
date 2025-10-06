import os
import io
import time
import base64
import zipfile
from typing import Dict, Any, List

import requests
import yaml
from flask import Flask, render_template, request, send_file, abort, redirect, url_for
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# ---------------------------
# Flask app & configuration
# ---------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# GitHub settings (provide via env on your host)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_MAIN = os.getenv("GITHUB_MAIN", "main")
GH_API = "https://api.github.com"

# List of document templates -> output filenames (must exist in templates/docs/)
DOC_TEMPLATES = [
    ("sow.md.j2", "SOW.md"),
    ("loe.md.j2", "LOE.md"),
    ("wbs.md.j2", "WBS.md"),
    ("hld.md.j2", "HLD.md"),
    ("lld.md.j2", "LLD.md"),
    ("atp.md.j2", "ATP.md"),
    ("asbuilt.md.j2", "AsBuilt.md"),
]

# ---------------------------
# Utilities
# ---------------------------

def jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader("templates/docs"),
        undefined=StrictUndefined,   # fail if a template references a missing key
        trim_blocks=True,
        lstrip_blocks=True,
    )

def render_markdown(data: Dict[str, Any]) -> Dict[str, str]:
    """Render all Markdown docs from Jinja templates."""
    env = jinja_env()
    rendered: Dict[str, str] = {}
    for tpl, outname in DOC_TEMPLATES:
        tmpl = env.get_template(tpl)
        rendered[outname]
