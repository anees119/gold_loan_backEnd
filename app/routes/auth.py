from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username, password = data.get("username", "").strip(), data.get("password", "")
    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify({"success": False, "message": "Invalid username or password"}), 401
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"success": True, "access_token": token,
                    "user": {"id": user.id, "full_name": user.full_name,
                             "username": user.username, "role": user.role,
                             "branch_id": user.branch_id}})

@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    return jsonify({"success": True, "user": {"id": user.id, "full_name": user.full_name,
                    "username": user.username, "role": user.role, "branch_id": user.branch_id}})
