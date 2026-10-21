# ============================================================
# Xime Glow - Servidor de mejora de fotos
# Quita el fondo, pone fondo lila de estudio y mejora luz/color.
# Desplegar en Render como Web Service (Python).
# ============================================================
import io
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from rembg import remove, new_session

app = Flask(__name__)
CORS(app)  # permite que la app (GitHub Pages) llame a este servidor

LADO = 1080
# Fondo lila (azul-morado tenue) elegido por el cliente
FONDO_C1 = (236, 228, 255)
FONDO_C2 = (201, 182, 255)

# El modelo se carga una sola vez al arrancar
_sesion = new_session("u2netp")


def construir_fondo():
    """Crea el fondo lila con un halo claro al centro."""
    base = Image.new("RGB", (LADO, LADO), FONDO_C1)
    top = Image.new("RGB", (LADO, LADO), FONDO_C2)
    mask = Image.new("L", (LADO, LADO))
    pm = mask.load()
    for y in range(LADO):
        for x in range(LADO):
            pm[x, y] = int(255 * ((x + y) / (2 * LADO)))
    base.paste(top, (0, 0), mask)
    halo = Image.new("L", (LADO, LADO), 0)
    hd = ImageDraw.Draw(halo)
    cx, cy, r = LADO // 2, int(LADO * 0.42), int(LADO * 0.58)
    for i in range(r, 0, -2):
        a = int(110 * (1 - i / r))
        hd.ellipse([cx - i, cy - i, cx + i, cy + i], fill=a)
    halo = halo.filter(ImageFilter.GaussianBlur(40))
    blanco = Image.new("RGB", (LADO, LADO), (255, 255, 255))
    base.paste(blanco, (0, 0), halo)
    return base.convert("RGBA")


def mejorar_producto(datos_imagen):
    """Recibe bytes de imagen, regresa bytes JPEG ya mejorados."""
    recorte = remove(datos_imagen, session=_sesion, post_process_mask=True)
    prod = Image.open(io.BytesIO(recorte)).convert("RGBA")

    bbox = prod.split()[3].getbbox()
    if bbox:
        prod = prod.crop(bbox)

    # mejora de luz/color
    rgb = prod.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(1.07)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.10)
    rgb = ImageEnhance.Color(rgb).enhance(1.12)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.15)
    prod = Image.merge("RGBA", (*rgb.split(), prod.split()[3]))

    lienzo = construir_fondo()

    margen = 0.80
    escala = min((LADO * margen) / prod.width, (LADO * margen) / prod.height)
    nw, nh = int(prod.width * escala), int(prod.height * escala)
    p = prod.resize((nw, nh), Image.LANCZOS)
    x = (LADO - nw) // 2
    y = (LADO - nh) // 2 - int(LADO * 0.015)

    # sombra suave de estudio
    sombra = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    alpha = p.split()[3]
    tinte = Image.new("RGBA", (nw, nh), (70, 20, 45, 150))
    sombra.paste(tinte, (x, y + int(LADO * 0.02)), alpha)
    sombra = sombra.filter(ImageFilter.GaussianBlur(28))
    lienzo = Image.alpha_composite(lienzo, sombra)

    capa = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    capa.paste(p, (x, y), p)
    lienzo = Image.alpha_composite(lienzo, capa)

    salida = io.BytesIO()
    lienzo.convert("RGB").save(salida, format="JPEG", quality=90)
    salida.seek(0)
    return salida


@app.route("/")
def inicio():
    return jsonify({"servicio": "Xime Glow - mejora de fotos", "estado": "ok"})


@app.route("/mejorar", methods=["POST"])
def mejorar():
    try:
        if "foto" not in request.files:
            return jsonify({"error": "No se recibió ninguna foto (campo 'foto')."}), 400
        archivo = request.files["foto"]
        datos = archivo.read()
        if not datos:
            return jsonify({"error": "La foto llegó vacía."}), 400
        resultado = mejorar_producto(datos)
        return send_file(resultado, mimetype="image/jpeg", download_name="producto.jpg")
    except Exception as e:
        return jsonify({"error": "No se pudo procesar la imagen: " + str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
