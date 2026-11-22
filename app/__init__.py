
from flask import Flask, jsonify
from flask_cors import CORS

from .config import Config
from .extensions import db, migrate, jwt


def create_app():
    app = Flask(__name__)

    # Load application configuration
    app.config.from_object(Config)

    # Validate required environment variables
    Config.validate()

    # Configure CORS
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config["CORS_ORIGINS"]
            }
        }
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Import models so Flask-Migrate can detect them
    from . import models  # noqa: F401

    # Import API blueprints
    from .routes.auth import auth_bp
    from .routes.branches import branches_bp
    from .routes.customers import customers_bp
    from .routes.enquiries import enquiries_bp

    # Register API routes
    app.register_blueprint(
        auth_bp,
        url_prefix="/api/auth"
    )

    app.register_blueprint(
        branches_bp,
        url_prefix="/api/branches"
    )

    app.register_blueprint(
        customers_bp,
        url_prefix="/api/customers"
    )

    app.register_blueprint(
        enquiries_bp,
        url_prefix="/api/enquiries"
    )

    # Health check
    @app.get("/api/health")
    def health():
        return jsonify({
            "success": True,
            "message": "Gold CRM API is running"
        }), 200

    # Handle 404 errors
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({
            "success": False,
            "message": "Endpoint not found"
        }), 404

    # Handle 500 errors
    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500

    return app
