from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.customer import Customer
from app.security import encrypt_field, mask_identifier

customers_bp = Blueprint("customers", __name__)

def customer_json(c):
    # Sensitive identifiers are never returned in full.
    return {"id": c.id, "customer_name": c.customer_name,
            "contact_number": c.contact_number, "gender": c.gender,
            "aadhaar": "stored" if c.aadhaar_encrypted else None,
            "pan": "stored" if c.pan_encrypted else None,
            "address": c.address, "created_at": c.created_at.isoformat() if c.created_at else None}

@customers_bp.post("")
@jwt_required()
def create_customer():
    data = request.get_json(silent=True) or {}
    name = (data.get("customer_name") or "").strip()
    phone = (data.get("contact_number") or "").strip()
    if not name or not phone:
        return jsonify({"success": False, "message": "customer_name and contact_number are required"}), 400
    customer = Customer(customer_name=name, contact_number=phone,
        gender=data.get("gender"), aadhaar_encrypted=encrypt_field(data.get("aadhaar")),
        pan_encrypted=encrypt_field(data.get("pan")), address=data.get("address"))
    db.session.add(customer)
    db.session.commit()
    return jsonify({"success": True, "data": customer_json(customer)}), 201

@customers_bp.get("")
@jwt_required()
def list_customers():
    search = (request.args.get("search") or "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
    query = Customer.query
    if search:
        query = query.filter(db.or_(Customer.customer_name.ilike(f"%{search}%"),
                                    Customer.contact_number.ilike(f"%{search}%")))
    pagination = query.order_by(Customer.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"success": True, "data": [customer_json(c) for c in pagination.items],
                    "pagination": {"page": page, "per_page": per_page,
                                   "total": pagination.total, "pages": pagination.pages}})
