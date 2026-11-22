from decimal import Decimal, InvalidOperation
from uuid import uuid4
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.customer import Customer
from app.models.branch import Branch
from app.models.enquiry import Enquiry, EnquiryProduct
from app.security import encrypt_field

enquiries_bp = Blueprint("enquiries", __name__)

def dec(value, field):
    try:
        number = Decimal(str(value if value not in (None, "") else "0"))
        if not number.is_finite():
            raise InvalidOperation
        return number
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a valid number")

def enquiry_json(e):
    return {
        "id": e.id, "enquiry_number": e.enquiry_number, "customer_id": e.customer_id,
        "customer_name": e.customer.customer_name if e.customer else None,
        "contact_number": e.customer.contact_number if e.customer else None,
        "branch_id": e.branch_id, "priority_level": e.priority_level,
        "pawner_name": e.pawner_name, "loan_amount": str(e.loan_amount or 0),
        "article_value": str(e.article_value or 0), "interest_percent": str(e.interest_percent or 0),
        "interest_amount": str(e.interest_amount or 0), "other_charges": str(e.other_charges or 0),
        "total_due": str(e.total_due or 0), "total_gross_weight": str(e.total_gross_weight or 0),
        "total_deduction": str(e.total_deduction or 0), "total_net_weight": str(e.total_net_weight or 0),
        "remarks": e.remarks, "status": e.status,
        "products": [{"id": p.id, "product_name": p.product_name,
                      "gross_weight": str(p.gross_weight), "deduction": str(p.deduction),
                      "net_weight": str(p.net_weight)} for p in e.products],
        "created_at": e.created_at.isoformat() if e.created_at else None
    }

@enquiries_bp.post("")
@jwt_required()
def create_enquiry():
    data = request.get_json(silent=True) or {}
    customer_data = data.get("customer") or {}
    customer_id = data.get("customer_id")
    branch_id = data.get("branch_id")
    if not branch_id or not db.session.get(Branch, branch_id):
        return jsonify({"success": False, "message": "A valid branch_id is required"}), 400
    if customer_id:
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return jsonify({"success": False, "message": "Customer not found"}), 404
    else:
        name = (customer_data.get("customer_name") or "").strip()
        phone = (customer_data.get("contact_number") or "").strip()
        if not name or not phone:
            return jsonify({"success": False, "message": "customer.customer_name and customer.contact_number are required"}), 400
        customer = Customer(customer_name=name, contact_number=phone,
            gender=customer_data.get("gender"), address=customer_data.get("address"),
            aadhaar_encrypted=encrypt_field(customer_data.get("aadhaar")),
            pan_encrypted=encrypt_field(customer_data.get("pan")))
        db.session.add(customer)
        db.session.flush()
    products = data.get("products") or []
    if not isinstance(products, list):
        return jsonify({"success": False, "message": "products must be an array"}), 400
    try:
        gross_total = Decimal("0")
        deduction_total = Decimal("0")
        normalized = []
        for index, item in enumerate(products, start=1):
            product_name = (item.get("product_name") or "").strip()
            if not product_name:
                raise ValueError(f"products[{index - 1}].product_name is required")
            gross = dec(item.get("gross_weight"), "gross_weight")
            deduction = dec(item.get("deduction"), "deduction")
            if gross < 0 or deduction < 0 or deduction > gross:
                raise ValueError(f"Invalid weights for product row {index}")
            net = gross - deduction
            gross_total += gross
            deduction_total += deduction
            normalized.append((product_name, gross, deduction, net))
        money_fields = {
            "loan_amount": dec(data.get("loan_amount"), "loan_amount"),
            "article_value": dec(data.get("article_value"), "article_value"),
            "interest_percent": dec(data.get("interest_percent"), "interest_percent"),
            "interest_amount": dec(data.get("interest_amount"), "interest_amount"),
            "other_charges": dec(data.get("other_charges"), "other_charges"),
            "total_due": dec(data.get("total_due"), "total_due"),
        }
        if any(v < 0 for v in money_fields.values()):
            raise ValueError("Financial amounts and interest percentage cannot be negative")
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    enquiry = Enquiry(
        enquiry_number=f"TEMP-{uuid4().hex}", customer_id=customer.id,
        branch_id=branch_id, created_by=int(get_jwt_identity()),
        priority_level=data.get("priority_level"), pawner_name=data.get("pawner_name"),
        remarks=data.get("remarks"), total_gross_weight=gross_total,
        total_deduction=deduction_total, total_net_weight=gross_total-deduction_total,
        **money_fields
    )
    db.session.add(enquiry)
    db.session.flush()
    enquiry.enquiry_number = f"ENQ-{enquiry.id:06d}"
    for name, gross, deduction, net in normalized:
        db.session.add(EnquiryProduct(enquiry_id=enquiry.id, product_name=name,
            gross_weight=gross, deduction=deduction, net_weight=net))
    db.session.commit()
    return jsonify({"success": True, "message": "Enquiry created successfully",
                    "data": enquiry_json(enquiry)}), 201

@enquiries_bp.get("")
@jwt_required()
def list_enquiries():
    search = (request.args.get("search") or "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
    query = Enquiry.query.join(Customer)
    if search:
        query = query.filter(db.or_(Enquiry.enquiry_number.ilike(f"%{search}%"),
                                    Customer.customer_name.ilike(f"%{search}%"),
                                    Customer.contact_number.ilike(f"%{search}%")))
    if request.args.get("branch_id", type=int):
        query = query.filter(Enquiry.branch_id == request.args.get("branch_id", type=int))
    pagination = query.order_by(Enquiry.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"success": True, "data": [enquiry_json(e) for e in pagination.items],
                    "pagination": {"page": page, "per_page": per_page,
                                   "total": pagination.total, "pages": pagination.pages}})

@enquiries_bp.get("/<int:enquiry_id>")
@jwt_required()
def get_enquiry(enquiry_id):
    enquiry = db.session.get(Enquiry, enquiry_id)
    if not enquiry:
        return jsonify({"success": False, "message": "Enquiry not found"}), 404
    return jsonify({"success": True, "data": enquiry_json(enquiry)})
