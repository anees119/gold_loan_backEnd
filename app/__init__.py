from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config
from .extensions import db, migrate, jwt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    from .routes.branches import branches_bp
    from .routes.customers import customers_bp
    from .routes.enquiries import enquiries_bp
    from .routes.loans import loans_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(branches_bp, url_prefix="/api/branches")
    app.register_blueprint(customers_bp, url_prefix="/api/customers")
    app.register_blueprint(enquiries_bp, url_prefix="/api/enquiries")
    app.register_blueprint(loans_bp, url_prefix="/api/loans")

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "message": "Gold CRM API is running"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app