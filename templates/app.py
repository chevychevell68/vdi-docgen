from flask import Flask
from blueprints.presales import presales_bp
from blueprints.outputs import outputs_bp
import os

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')

    # Register blueprints
    app.register_blueprint(presales_bp)
    app.register_blueprint(outputs_bp)

    @app.route('/')
    def index():
        return 'VDI DocGen is running'

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
