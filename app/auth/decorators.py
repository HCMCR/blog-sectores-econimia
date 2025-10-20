# app/auth/decorators.py
from functools import wraps
from flask import request, jsonify, g
import jwt, os

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "supersecret")

class LoggedDict(dict):
    def __setitem__(self, key, value):
        if self.get(key) != value:
            import traceback
            print(f"🛑 g.current_user['{key}'] cambiado: {self.get(key)} -> {value}")
            traceback.print_stack()
        super().__setitem__(key, value)

def jwt_required_local(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            print("⚠️ No se recibió Authorization válido")
            return jsonify({"error": "Token requerido"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            
            membership_level = str(payload.get("membership_level", "platinum")).replace(" ", "").lower()
            
            g.current_user = LoggedDict({
                "id": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "membership_level": membership_level,
                "is_admin": payload.get("is_admin", False),
                "is_buyer": payload.get("is_buyer", False),
                "is_seller": payload.get("is_seller", False),
            })

            print("🔹 g.current_user inicial:", g.current_user)

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Token inválido: {str(e)}"}), 401

        return f(*args, **kwargs)
    return decorated




def membership_required(levels_allowed):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                return jsonify({"error": "Usuario no autenticado"}), 401

            # ⚡ Solo para validar, no sobreescribas g.current_user
            clean_level = user.get("membership_level", "").replace(" ", "").lower()

            # Admin siempre puede
            if user.get("role") == "admin":
                return f(*args, **kwargs)

            if clean_level not in [lvl.lower() for lvl in levels_allowed]:
                return jsonify({
                    "error": f"Nivel de membresía '{user.get('membership_level')}' no autorizado"
                }), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(g, "current_user", None):
            return jsonify({"error": "No logueado"}), 401
        return f(*args, **kwargs)
    return decorated