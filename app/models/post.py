from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSON


# app/models/post.py
class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    
    # 🧠 SEO / Contenido principal
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    keywords = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=True)

    # 🧱 Bloques de contenido dinámico
    content_blocks = db.Column(JSON, nullable=False, default=[])

    # 🖼️ Imagen destacada
    featured_image = db.Column(db.String, nullable=True)
    featured_image_public_id = db.Column(db.String, nullable=True)

    # 🏢 Relación con compañía (viene desde Infinity)
    company_id = db.Column(db.Integer, nullable=True)

    #limite de palabras y limite por semana
    word_count = db.Column(db.Integer, default=0)
    week_number = db.Column(db.Integer, nullable=True)

    # 👤 Datos del autor (vienen desde Infinity)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(150), nullable=False)

    # 🌟 Nuevo campo para slug
    slug = db.Column(db.String(255), unique=True, nullable=False)

    # ⏰ Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # ✅ Método para devolverlo como JSON-friendly dict
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
            "category": self.category,
            "featured_image": self.featured_image,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "slug": self.slug,
            "content_blocks": self.content_blocks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Post {self.title}>"
