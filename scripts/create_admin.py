import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all()
    username = input("Admin username: ").strip()
    full_name = input("Admin full name: ").strip()
    password = input("Admin password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Use a password of at least 12 characters.")
    if User.query.filter_by(username=username).first():
        raise SystemExit("Username already exists.")
    user = User(username=username, full_name=full_name, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Admin '{username}' created.")
