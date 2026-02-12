import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from database import init_app
from api import routes_pipeline, routes_nodes

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(test_config)

    # Database
    init_app(app)
    
    # CORS
    # Allow all for dev convenience or configure from env
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Blueprints
    app.register_blueprint(routes_pipeline.bp)
    app.register_blueprint(routes_nodes.bp)

    @app.route('/health')
    def health():
        return jsonify({"status": "ok"})

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8002)) # Default to 8002 to avoid conflict with V1 (8001)
    app.run(host='0.0.0.0', port=port, debug=True)
