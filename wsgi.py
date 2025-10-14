# wsgi.py - Gunicorn entrypoint
from app import create_app

app = create_app()

# Optional: simple health route if needed when running with `python wsgi.py`
if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 5000, app, use_debugger=True, use_reloader=True)
