# app/routes/__init__.py
from flask import Flask

def register_routes(app: Flask):
    """
    Registrar todos los blueprints de la carpeta routes.
    Llamá a register_routes(app) desde app.create_app().
    """
    # Import local para evitar problemas de import circular al inicializar la app
    from .post_routes import post_bp
    from .auth import auth_bp
    from .upload_routes import upload_bp
    app.register_blueprint(post_bp, url_prefix="/posts")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(upload_bp, url_prefix="/")


