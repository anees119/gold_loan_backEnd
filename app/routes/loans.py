import os
from decimal import Decimal, InvalidOperation
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.loan import Loan, LoanItem
from app.security import encrypt_field

loans_bp = Blueprint("loans", __name__)

# ── upload config ─────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads", "loans")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_file(file_obj, sub):
    if not file_obj or file_obj.filename == "":
        return None
    if not _allowed(file_obj.filename):
        raise ValueError(f"File type not allowed: {file_obj.filename}")
    folder = os.path.join(UPLOAD_FOLDER, sub)
    os.makedirs(folder, exist_ok=True)
    fname = secure_filename(file_obj.filename)
    file_obj.save(os.path.join(folder, fname))
    return f"uploads/loans/{sub}/{fname}"


# ── helpers ───────────────────────────────────────────────────────────────────
def _dec(value, field):
    try:
        n = Decimal(str(value if value not in (None, "") else "0"))
        if not n.is_finite():
            raise InvalidOperation
        return n
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be a valid number")


def _parse_date(value, field):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"{field} must be YYYY-MM-DD")


def _item_json(item):
    return {
        "id":           item.id,
        "product_name": item.product_name,
        "quantity":     item.quantity,
        "gross_weight": str(item.gross_weight),
        "deduction":    str(item.deduction),
        "net_weight":   str(item.net_weight),
        "purity":       item.purity,
    }


def _loan_json(loan):
    return {
        "id":                  loan.id,
        "customer_name":       loan.customer_name,
        "relation_type":       loan.relation_type,
        "relation_name":       loan.relation_name,
        "contact_number":      loan.contact_number,
        "alternative_number":  loan.alternative_number,
        "date_of_birth":       loan.date_of_birth.isoformat() if loan.date_of_birth else None,
        "gender":              loan.gender,
        "email":               loan.email,
        "aadhaar_number":      "stored" if loan.aadhaar_number else None,
        "pan_number":          "stored" if loan.pan_number else None,
        "nominee_name":        loan.nominee_name,
        "current_address":     loan.current_address,
        "permanent_address":   loan.permanent_address,
        "customer_photo":      loan.customer_photo,
        "items_image":         loan.items_image,
        "loan_amount":         str(loan.loan_amount or 0),
        "loan_type":           loan.loan_type,
        "article_value":       str(loan.article_value or 0),
        "interest_rate":       str(loan.interest_rate or 0),
        "total_interest":      str(loan.total_interest or 0),
        "interest_mode":       loan.interest_mode,
        "loan_tenure":         loan.loan_tenure,
        "payment_type":        loan.payment_type,
        "total_quantity":      loan.total_quantity,
        "total_gross_weight":  str(loan.total_gross_weight or 0),
        "total_deduction":     str(loan.total_deduction or 0),
        "total_net_weight":    str(loan.total_net_weight or 0),
        "remarks":             loan.remarks,
        "notes":               loan.notes,
        "loan_date":           loan.loan_date.isoformat() if loan.loan_date else None,
        "loan_status":         loan.loan_status,
        "created_at":          loan.created_at.isoformat() if loan.created_at else None,
        "updated_at":          loan.updated_at.isoformat() if loan.updated_at else None,
        "items":               [_item_json(i) for i in loan.items],
    }


def _extract_items(raw_items):
    if not isinstance(raw_items, list):
        raise ValueError("items must be a JSON array")
    normalized = []
    gross_total = Decimal("0")
    deduction_total = Decimal("0")
    qty_total = 0
    for idx, row in enumerate(raw_items, start=1):
        name = (row.get("product_name") or "").strip()
        if not name:
            raise ValueError(f"items[{idx - 1}].product_name is required")
        qty    = int(row.get("quantity", 1) or 1)
        gross  = _dec(row.get("gross_weight"), "gross_weight")
        deduct = _dec(row.get("deduction"),    "deduction")
        if gross < 0 or deduct < 0 or deduct > gross:
            raise ValueError(f"Invalid weights at items[{idx - 1}]")
        net = gross - deduct
        gross_total     += gross
        deduction_total += deduct
        qty_total       += qty
        normalized.append({
            "product_name": name,
            "quantity":     qty,
            "gross_weight": gross,
            "deduction":    deduct,
            "net_weight":   net,
            "purity":       (row.get("purity") or "").strip() or None,
        })
    return normalized, gross_total, deduction_total, gross_total - deduction_total, qty_total


# ── POST /api/loans ───────────────────────────────────────────────────────────
@loans_bp.post("")
@jwt_required()
def create_loan():
    is_form = request.content_type and "multipart" in request.content_type
    if is_form:
        import json as _json
        data = request.form.to_dict()
        raw_items = _json.loads(data.get("items", "[]") or "[]")
    else:
        data = request.get_json(silent=True) or {}
        raw_items = data.get("items", [])

    name  = (data.get("customer_name") or "").strip()
    phone = (data.get("contact_number") or "").strip()
    if not name or not phone:
        return jsonify({"success": False,
                        "message": "customer_name and contact_number are required"}), 400
    try:
        items_norm, g_total, d_total, n_total, qty_total = _extract_items(raw_items)
        loan_amount    = _dec(data.get("loan_amount"),    "loan_amount")
        article_value  = _dec(data.get("article_value"),  "article_value")
        interest_rate  = _dec(data.get("interest_rate"),  "interest_rate")
        total_interest = _dec(data.get("total_interest"), "total_interest")
        loan_date      = _parse_date(data.get("loan_date"),     "loan_date")
        dob            = _parse_date(data.get("date_of_birth"), "date_of_birth")
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    try:
        customer_photo = _save_file(request.files.get("customer_photo"), "photos")
        items_image    = _save_file(request.files.get("items_image"),    "items")
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    loan = Loan(
        customer_name      = name,
        relation_type      = data.get("relation_type"),
        relation_name      = data.get("relation_name"),
        contact_number     = phone,
        alternative_number = data.get("alternative_number"),
        date_of_birth      = dob,
        gender             = data.get("gender"),
        email              = data.get("email"),
        aadhaar_number     = encrypt_field(data.get("aadhaar_number")),
        pan_number         = encrypt_field(data.get("pan_number")),
        nominee_name       = data.get("nominee_name"),
        current_address    = data.get("current_address"),
        permanent_address  = data.get("permanent_address"),
        customer_photo     = customer_photo,
        items_image        = items_image,
        loan_amount        = loan_amount,
        loan_type          = data.get("loan_type", "Normal"),
        article_value      = article_value,
        interest_rate      = interest_rate,
        total_interest     = total_interest,
        interest_mode      = data.get("interest_mode"),
        loan_tenure        = data.get("loan_tenure"),
        payment_type       = data.get("payment_type"),
        total_quantity     = qty_total,
        total_gross_weight = g_total,
        total_deduction    = d_total,
        total_net_weight   = n_total,
        remarks            = data.get("remarks"),
        notes              = data.get("notes"),
        loan_date          = loan_date,
        loan_status        = data.get("loan_status", "active"),
    )
    db.session.add(loan)
    db.session.flush()
    for row in items_norm:
        db.session.add(LoanItem(loan_id=loan.id, **row))
    db.session.commit()
    return jsonify({"success": True, "message": "Loan created successfully",
                    "data": _loan_json(loan)}), 201


# ── GET /api/loans ────────────────────────────────────────────────────────────
@loans_bp.get("")
@jwt_required()
def list_loans():
    search   = (request.args.get("search") or "").strip()
    status   = (request.args.get("loan_status") or "").strip()
    page     = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)

    query = Loan.query
    if search:
        query = query.filter(db.or_(
            Loan.customer_name.ilike(f"%{search}%"),
            Loan.contact_number.ilike(f"%{search}%"),
        ))
    if status:
        query = query.filter(Loan.loan_status == status)

    pagination = query.order_by(Loan.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return jsonify({
        "success": True,
        "data": [_loan_json(l) for l in pagination.items],
        "pagination": {"page": page, "per_page": per_page,
                       "total": pagination.total, "pages": pagination.pages}
    })


# ── GET /api/loans/<id> ───────────────────────────────────────────────────────
@loans_bp.get("/<int:loan_id>")
@jwt_required()
def get_loan(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    return jsonify({"success": True, "data": _loan_json(loan)})


# ── PUT /api/loans/<id> ───────────────────────────────────────────────────────
@loans_bp.put("/<int:loan_id>")
@jwt_required()
def update_loan(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404

    is_form = request.content_type and "multipart" in request.content_type
    if is_form:
        import json as _json
        data = request.form.to_dict()
        raw_items = _json.loads(data.get("items", "[]") or "[]")
    else:
        data = request.get_json(silent=True) or {}
        raw_items = data.get("items", [])

    try:
        if "loan_amount"    in data: loan.loan_amount    = _dec(data["loan_amount"],    "loan_amount")
        if "article_value"  in data: loan.article_value  = _dec(data["article_value"],  "article_value")
        if "interest_rate"  in data: loan.interest_rate  = _dec(data["interest_rate"],  "interest_rate")
        if "total_interest" in data: loan.total_interest = _dec(data["total_interest"], "total_interest")
        if "loan_date"      in data: loan.loan_date      = _parse_date(data["loan_date"],     "loan_date")
        if "date_of_birth"  in data: loan.date_of_birth  = _parse_date(data["date_of_birth"], "date_of_birth")
        if raw_items:
            items_norm, g_total, d_total, n_total, qty_total = _extract_items(raw_items)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    for field in ("customer_name", "relation_type", "relation_name", "contact_number",
                  "alternative_number", "gender", "email", "nominee_name",
                  "current_address", "permanent_address", "loan_type",
                  "interest_mode", "loan_tenure", "payment_type",
                  "remarks", "notes", "loan_status"):
        if field in data:
            setattr(loan, field, data[field])

    if "aadhaar_number" in data: loan.aadhaar_number = encrypt_field(data["aadhaar_number"])
    if "pan_number"     in data: loan.pan_number     = encrypt_field(data["pan_number"])

    try:
        if request.files.get("customer_photo"):
            loan.customer_photo = _save_file(request.files["customer_photo"], "photos")
        if request.files.get("items_image"):
            loan.items_image = _save_file(request.files["items_image"], "items")
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    if raw_items:
        for old in list(loan.items):
            db.session.delete(old)
        db.session.flush()
        for row in items_norm:
            db.session.add(LoanItem(loan_id=loan.id, **row))
        loan.total_quantity     = qty_total
        loan.total_gross_weight = g_total
        loan.total_deduction    = d_total
        loan.total_net_weight   = n_total

    db.session.commit()
    return jsonify({"success": True, "message": "Loan updated successfully",
                    "data": _loan_json(loan)})


# ── DELETE /api/loans/<id> ────────────────────────────────────────────────────
@loans_bp.delete("/<int:loan_id>")
@jwt_required()
def delete_loan(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    db.session.delete(loan)
    db.session.commit()
    return jsonify({"success": True, "message": "Loan deleted successfully"})


# ── PATCH /api/loans/<id>/status ─────────────────────────────────────────────
@loans_bp.patch("/<int:loan_id>/status")
@jwt_required()
def update_loan_status(loan_id):
    loan = db.session.get(Loan, loan_id)
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    data   = request.get_json(silent=True) or {}
    status = (data.get("loan_status") or "").strip()
    valid  = {"active", "closed", "defaulted", "pending"}
    if status not in valid:
        return jsonify({"success": False,
                        "message": f"loan_status must be one of: {', '.join(sorted(valid))}"}), 400
    loan.loan_status = status
    db.session.commit()
    return jsonify({"success": True,
                    "message": f"Loan status updated to '{status}'",
                    "data": {"id": loan.id, "loan_status": loan.loan_status}})