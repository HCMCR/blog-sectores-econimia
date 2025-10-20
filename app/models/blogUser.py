from datetime import datetime
from app.extensions import db

class BlogUser(db.Model):
    __tablename__ = "blog_users"
    
    id = db.Column(db.Integer, primary_key=True)
    infinity_id = db.Column(db.Integer, nullable=False, unique=True)  # id del usuario en Infinity
    email = db.Column(db.String(120), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=False)
    
    role = db.Column(db.String(20), default="user")  # 'user' o 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
