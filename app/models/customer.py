from app.extensions import db

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False, index=True)
    contact_number = db.Column(db.String(20), nullable=False, index=True)
    gender = db.Column(db.String(30))
    aadhaar_encrypted = db.Column(db.Text)
    pan_encrypted = db.Column(db.Text)
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
