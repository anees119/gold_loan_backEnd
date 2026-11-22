from app.extensions import db

class Branch(db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    branch_name = db.Column(db.String(120), nullable=False, unique=True)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {"id": self.id, "branch_name": self.branch_name,
                "address": self.address, "phone": self.phone,
                "is_active": self.is_active}
