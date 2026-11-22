from app.extensions import db

class Enquiry(db.Model):
    __tablename__ = "enquiries"
    id = db.Column(db.Integer, primary_key=True)
    enquiry_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    priority_level = db.Column(db.String(30))
    pawner_name = db.Column(db.String(150))
    loan_amount = db.Column(db.Numeric(14, 2), default=0)
    article_value = db.Column(db.Numeric(14, 2), default=0)
    interest_percent = db.Column(db.Numeric(7, 2), default=0)
    interest_amount = db.Column(db.Numeric(14, 2), default=0)
    other_charges = db.Column(db.Numeric(14, 2), default=0)
    total_due = db.Column(db.Numeric(14, 2), default=0)
    total_gross_weight = db.Column(db.Numeric(12, 3), default=0)
    total_deduction = db.Column(db.Numeric(12, 3), default=0)
    total_net_weight = db.Column(db.Numeric(12, 3), default=0)
    remarks = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    customer = db.relationship("Customer")
    products = db.relationship("EnquiryProduct", cascade="all, delete-orphan", lazy=True)

class EnquiryProduct(db.Model):
    __tablename__ = "enquiry_products"
    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiries.id"), nullable=False)
    product_name = db.Column(db.String(180), nullable=False)
    gross_weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    deduction = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    net_weight = db.Column(db.Numeric(12, 3), nullable=False, default=0)
