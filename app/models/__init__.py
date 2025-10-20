# app/models/__init__.py
"""
Paquete de modelos de la aplicación.
Importa aquí los modelos para que puedan ser referenciados como:
from app.models import Post
"""
from .post import Post

__all__ = ["Post","BlogUser"]
