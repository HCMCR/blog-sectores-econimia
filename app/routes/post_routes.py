from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.post import Post
from slugify import slugify
from app.auth.decorators import login_required, membership_required, jwt_required_local
from app.utils.membership_rules import (
    can_user_post,
    validate_post_length,
    get_current_week_number,
    count_words_from_blocks,
    get_membership_limits  # <-- reemplaza get_word_limit
)

post_bp = Blueprint("posts", __name__)

def generate_unique_slug(title, user_id):
    """Genera un slug único agregando timestamp si ya existe"""
    base_slug = slugify(title)
    slug = base_slug
    i = 1
    while Post.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{i}-{user_id}"
        i += 1
    return slug

# 🟢 Crear un nuevo post
@post_bp.route("/", methods=["POST"])
@jwt_required_local
@membership_required(["platinum", "gold", "silver", "bronze"])
def create_post():
    user = g.current_user.copy()
    user["membership_level"] = user.get("membership_level", "bronze").replace(" ", "").lower()

    data = request.get_json() or {}
    week_number = get_current_week_number()

    # Validar campos obligatorios
    required_fields = ["title", "description", "content_blocks"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Faltan campos obligatorios: {', '.join(missing)}"}), 400

    # Validar límite semanal
    current_week_posts = Post.query.filter_by(user_id=user["id"], week_number=week_number).count()
    if not can_user_post(user, current_week_posts):
        return jsonify({"error": "Has alcanzado tu límite de publicaciones semanales."}), 403

    # Contar palabras
    content_blocks = data.get("content_blocks", [])
    word_count = count_words_from_blocks(content_blocks)
    if not validate_post_length(user, word_count):
        return jsonify({
            "error": "Superaste el límite de palabras permitido para tu membresía.",
            "limit": get_membership_limits(user["membership_level"]),
            "used": word_count
        }), 400

    # Slug único
    slug = generate_unique_slug(data["title"], user["id"])
    print("✅ Membership real esto es desde el post:", g.current_user["membership_level"])
    print("Tipo de g.current_user esto es desde el post:", type(g.current_user))
    print("📝 current_week_posts:", current_week_posts)
    print("📝 can_user_post:", can_user_post(user, current_week_posts))
    print("📝 validate_post_length:", validate_post_length(user, word_count))
    print("📝 word_count:", word_count)
    print("📝 membership_level limpio:", user.get("membership_level").lower())

    # Imagen destacada (Cloudinary) opcional
    featured_image_url = data.get("featured_image")  # frontend ya subió la imagen y envía la URL
    featured_image_public_id = data.get("featured_image_public_id")

    # Crear post
    new_post = Post(
        title=data["title"],
        description=data["description"],
        keywords=data.get("keywords"),
        category=data["category"],
        company_id=data.get("company_id"),
        featured_image=featured_image_url,
        featured_image_public_id=featured_image_public_id,
        content_blocks=content_blocks,
        user_id=user["id"],
        user_name=user["username"],
        word_count=word_count,
        week_number=week_number,
        slug=slug
    )

    try:
        db.session.add(new_post)
        db.session.commit()
        return jsonify({"message": "Post creado exitosamente", "data": new_post.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error al guardar el post", "details": str(e)}), 500



# 🟡 Editar post (solo dueño o admin)
@post_bp.route("/<int:id>", methods=["PUT"])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    user = g.current_user

    # 🔒 Validar permisos
    if post.user_id != int(user["id"]) and user.get("role") != "admin":
        return jsonify({"error": "No autorizado"}), 403

    # 📦 Obtener datos
    data = request.get_json() or {}
    new_blocks = data.get("content_blocks", post.content_blocks)

    # 📏 Contar palabras y validar límite por membresía
    word_count = count_words_from_blocks(new_blocks)
    if not validate_post_length(user, word_count):
        return jsonify({
            "error": "Superaste el límite de palabras permitido para tu membresía.",
            "limit": get_membership_limits(user.get("membership_level")),
            "used": word_count
        }), 400

    # 🔠 Guardar título original antes de modificarlo
    old_title = post.title

    # 📝 Actualizar campos editables
    post.title = data.get("title", post.title)
    post.description = data.get("description", post.description)
    post.keywords = data.get("keywords", post.keywords)
    post.category = data.get("category", post.category)
    post.content_blocks = new_blocks
    post.word_count = word_count
    post.updated_at = datetime.utcnow()

    # 🖼️ Imagen destacada (solo si viene explícitamente en la data)
    # Aquí se actualiza solo si el front ya tiene la URL final de la imagen subida
    if "featured_image" in data:
        post.featured_image = data["featured_image"] or None

    # 🧭 Actualizar slug si el título cambió (y solo si realmente cambió)
    if "title" in data and data["title"] != old_title:
        post.slug = generate_unique_slug(data["title"], user["id"])

    try:
        db.session.commit()
        return jsonify({
            "message": "Post actualizado correctamente",
            "data": post.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al actualizar post: {e}")
        return jsonify({
            "error": "Error al actualizar el post",
            "details": str(e)
        }), 500



# 🟣 Listar posts (paginado + filtros opcionales)
@post_bp.route("/", methods=["GET"])
def get_posts():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 12, type=int), 20)  # máximo 50
        company_id = request.args.get("company_id", type=int)
        category = request.args.get("category", type=str)

        query = Post.query

        if company_id:
            query = query.filter_by(company_id=company_id)
        # if category:
        #     query = query.filter(Post.category.ilike(category))  # case-insensitive

        pagination = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            "posts": [{
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "description": p.description,
                "category": p.category,
                "created_at": p.created_at.isoformat(),
                "featured_image": p.featured_image,
                "user_name": p.user_name,
                "word_count": p.word_count
            } for p in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page
        }), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener los posts", "details": str(e)}), 500


# 🔵 Ver un solo post (por ID o slug)
@post_bp.route("/<string:identifier>", methods=["GET"])
def get_post_detail(identifier):
    post = None
    if identifier.isdigit():
        post = Post.query.get(int(identifier))
    else:
        post = Post.query.filter_by(slug=identifier).first()

    if not post:
        return jsonify({"error": "Post no encontrado"}), 404

    return jsonify({
        "id": post.id,
        "slug": post.slug,
        "title": post.title,
        "description": post.description,
        "keywords": post.keywords,
        "category": post.category,
        "featured_image": post.featured_image,
        "content_blocks": post.content_blocks,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "author": post.user_name
    }), 200

@post_bp.route("/my-posts", methods=["GET"])
@login_required
def get_my_posts():
    user = g.current_user
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)

    # Si es admin, puede ver todos los posts
    if user.get("is_admin"):
        query = Post.query
    else:
        query = Post.query.filter_by(user_id=user["id"])

    pagination = query.order_by(Post.created_at.desc()) \
                      .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "posts": [p.to_dict() for p in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200


import cloudinary
import cloudinary.uploader

# 🔴 Borrar post (dueño o admin) + imagen en Cloudinary
@post_bp.route("/<int:id>", methods=["DELETE"])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    user = g.current_user

    # 🔒 Validar permisos: dueño o admin
    if post.user_id != int(user["id"]) and user.get("role") != "admin":
        return jsonify({"error": "No autorizado"}), 403

    try:
        # 🔹 Borrar imagen destacada de Cloudinary si existe
        if post.featured_image_public_id:
            cloudinary.uploader.destroy(post.featured_image_public_id)

        # 🔹 Borrar post de la DB
        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": "Post y imagen eliminados correctamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Error al eliminar el post",
            "details": str(e)
        }), 500
