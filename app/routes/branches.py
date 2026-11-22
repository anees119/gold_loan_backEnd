from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.branch import Branch

branches_bp = Blueprint("branches", __name__)

@branches_bp.get("")
@jwt_required()
def list_branches():
    rows = Branch.query.order_by(Branch.branch_name).all()
    return jsonify({"success": True, "data": [b.to_dict() for b in rows]})

@branches_bp.post("")
@jwt_required()
def create_branch():
    data = request.get_json(silent=True) or {}
    name = (data.get("branch_name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "branch_name is required"}), 400
    if Branch.query.filter_by(branch_name=name).first():
        return jsonify({"success": False, "message": "Branch already exists"}), 409
    branch = Branch(branch_name=name, address=data.get("address"), phone=data.get("phone"))
    db.session.add(branch)
    db.session.commit()
    return jsonify({"success": True, "data": branch.to_dict()}), 201
