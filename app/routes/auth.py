# app/routes/auth.py
from flask import Blueprint, request, jsonify
import requests
import jwt
import os
from datetime import datetime, timedelta
from app.extensions import db
from app.models.blogUser import BlogUser

auth_bp = Blueprint("auth", __name__)

INFINITY_LOGIN_URL = "https://infinity-gainers.onrender.com/users/login"  # login Infinity

def normalize_membership(name):
    mapping = {
        "bronce": "bronze",
        "bronze": "bronze",
        "silver": "silver",
        "gold": "gold",
        "platinum": "platinum"
    }
    if not name:
        return "platinum"
    return mapping.get(name.strip().lower(), "platinum")

@auth_bp.route("/", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    try:
        # 🔐 Login en Infinity
        response = requests.post(INFINITY_LOGIN_URL, json={"email": email, "password": password}, timeout=5)
        if response.status_code != 200:
            return jsonify({"error": "Invalid credentials"}), 401

        infinity_user = response.json()

        # 🧼 Normalizar y blindar membership_level
        raw_level = str(infinity_user.get("membership_level", "")).strip()
        membership_level = normalize_membership(raw_level)  # tu función personalizada
        if not membership_level:
            return jsonify({"error": f"Invalid membership level: '{raw_level}'"}), 400

        is_admin = bool(infinity_user.get("is_admin", False))
        is_buyer = bool(infinity_user.get("is_buyer", False))
        is_seller = bool(infinity_user.get("is_seller", False))

        # 🧩 Crear o actualizar usuario local
        user = BlogUser.query.filter_by(infinity_id=infinity_user.get("user_id")).first()
        if not user:
            user = BlogUser(
                infinity_id=infinity_user.get("user_id"),
                email=email,
                username=email.split("@")[0],
                role="admin" if is_admin else "user"
            )
            db.session.add(user)
        else:
            user.email = email
            user.role = "admin" if is_admin else "user"
        db.session.commit()

        # 🛡️ Generar JWT
        token_payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "membership_level": membership_level,
            "is_admin": is_admin,
            "is_buyer": is_buyer,
            "is_seller": is_seller,
            "exp": datetime.utcnow() + timedelta(hours=8)
        }

        token = jwt.encode(token_payload, os.environ.get("JWT_SECRET_KEY"), algorithm="HS256")

        print(f"✅ Login exitoso: {user.username} / Nivel: {membership_level}")

        return jsonify({
            "access_token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "membership_level": membership_level,
                "is_admin": is_admin,
                "is_buyer": is_buyer,
                "is_seller": is_seller
            }
        })

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error de conexión con Infinity: {e}")
        return jsonify({"error": "Error de conexión con Infinity"}), 502
    except Exception as e:
        print(f"❌ Error inesperado en login: {e}")
        return jsonify({"error": "Error interno en login"}), 500