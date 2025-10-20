# app/__init__.py
import jwt
import cloudinary
from flask import request, g
from app.config import Config
from flask import Flask
from app.extensions import db, migrate, cors
from app.routes import register_routes  # <- usar el init de routes
import os
import requests

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)

# 🔹 Clase para loguear cambios en g.current_user
class LoggedDict(dict):
    def __setitem__(self, key, value):
        if key == "membership_level" and self.get(key) != value:
            import traceback
            print(f"🛑 g.current_user['membership_level'] cambiado: {self.get(key)} -> {value}")
            traceback.print_stack()
        super().__setitem__(key, value)

# app/__init__.py o donde cargas el user desde el token
def load_user():
    auth_header = request.headers.get("Authorization", "")
    g.current_user = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])

            membership_level = str(payload.get("membership_level", "platinum")).replace(" ", "").strip().lower()

            g.current_user = LoggedDict({
                "id": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "membership_level": membership_level,
                "is_admin": payload.get("is_admin", False),
                "is_buyer": payload.get("is_buyer", False),
                "is_seller": payload.get("is_seller", False),
            })

            # 🔹 Log justo después de decodificar el token
            print("🔹 JWT payload crudo:", payload)
            print("🔹 g.current_user inicial:", g.current_user)

        except jwt.ExpiredSignatureError:
            print("⚠️ Token expirado")
        except jwt.InvalidTokenError as e:
            print("❌ Token inválido:", e)
    else:
        print("⚠️ No se recibió Authorization válido")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"]
    )

    # Registrar blueprints centralizado
    register_routes(app)

    @app.before_request
    def before_request():
        load_user()

    return app
