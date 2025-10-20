# app/routes/upload_routes.py
from flask import Blueprint, request, jsonify
import cloudinary.uploader
import imghdr

upload_bp = Blueprint("upload", __name__)

# Configuración
ALLOWED_EXTENSIONS = ["jpeg", "jpg", "png", "webp", "gif"]
MAX_SIZE = 150 * 1024  # 150 KB

@upload_bp.route("/upload-image", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No se encontró archivo 'image'"}), 400

    file = request.files["image"]

    # Validar tamaño
    file.seek(0, 2)  # mover al final
    size = file.tell()
    file.seek(0)     # volver al inicio
    if size > MAX_SIZE:
        return jsonify({"error": "La imagen no puede superar los 150 KB"}), 400

    # Validar tipo
    file_type = imghdr.what(file)
    if file_type not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Tipo de imagen no permitido: {file_type}"}), 400

    try:
        # Subir a Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder="blog_featured_images",
            resource_type="image"
        )

        url = result.get("secure_url")
        public_id = result.get("public_id")

        if not url:
            raise Exception("No se recibió URL de Cloudinary")

        return jsonify({"url": url, "public_id": public_id}), 200

    except Exception as e:
        print("❌ Error al subir imagen a Cloudinary:", e)
        return jsonify({
            "error": "Error al subir imagen",
            "details": str(e)
        }), 500
        
