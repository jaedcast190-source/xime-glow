# ============================================================
# Xime Glow - Servidor (fotos + sincronización de datos)
# - /mejorar : quita el fondo, pone fondo lila y mejora la foto
# - /datos   : guarda y entrega el estado de la app (sincroniza PC y celular)
# Desplegar en Render como Web Service (Python).
# ============================================================
import io, os, json, sqlite3, datetime
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from rembg import remove, new_session

app = Flask(__name__)
CORS(app)

# ---------- Base de datos (SQLite) ----------
# Si hay disco persistente montado en /var/data lo usa (datos permanentes).
# Si no, usa /tmp (funciona, pero se borra al reiniciar: para pruebas).
CARPETA_DATOS = os.environ.get("DATA_DIR", "/var/data")
if not os.path.isdir(CARPETA_DATOS):
    try:
        os.makedirs(CARPETA_DATOS, exist_ok=True)
    except Exception:
        CARPETA_DATOS = "/tmp"
RUTA_DB = os.path.join(CARPETA_DATOS, "ximeglow.db")

# PIN compartido opcional (si lo configuras en Render como SYNC_PIN,
# la app debe mandar el mismo para leer/escribir).
PIN_SERVIDOR = os.environ.get("SYNC_PIN", "").strip()


def conexion():
    con = sqlite3.connect(RUTA_DB)
    con.execute("CREATE TABLE IF NOT EXISTS estado (id INTEGER PRIMARY KEY, json TEXT, actualizado TEXT)")
    return con


def pin_valido(pin):
    if not PIN_SERVIDOR:
        return True  # sin pin configurado, abierto
    return (pin or "") == PIN_SERVIDOR


# ---------- Mejora de fotos ----------
LADO = 1080
FONDO_C1 = (236, 228, 255)  # lila claro
FONDO_C2 = (201, 182, 255)  # morado tenue
_sesion = new_session("u2netp")


def construir_fondo():
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
    recorte = remove(datos_imagen, session=_sesion, post_process_mask=True)
    prod = Image.open(io.BytesIO(recorte)).convert("RGBA")
    bbox = prod.split()[3].getbbox()
    if bbox:
        prod = prod.crop(bbox)
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


# ---------- Rutas ----------
@app.route("/")
def inicio():
    return jsonify({"servicio": "Xime Glow", "estado": "ok", "almacen": RUTA_DB})


@app.route("/mejorar", methods=["POST"])
def mejorar():
    try:
        if "foto" not in request.files:
            return jsonify({"error": "No se recibió ninguna foto (campo 'foto')."}), 400
        datos = request.files["foto"].read()
        if not datos:
            return jsonify({"error": "La foto llegó vacía."}), 400
        resultado = mejorar_producto(datos)
        return send_file(resultado, mimetype="image/jpeg", download_name="producto.jpg")
    except Exception as e:
        return jsonify({"error": "No se pudo procesar la imagen: " + str(e)}), 500


@app.route("/datos", methods=["GET"])
def leer_datos():
    try:
        if not pin_valido(request.args.get("pin")):
            return jsonify({"error": "PIN incorrecto."}), 403
        con = conexion()
        fila = con.execute("SELECT json, actualizado FROM estado WHERE id=1").fetchone()
        con.close()
        if not fila:
            return jsonify({"estado": None, "actualizado": None})
        return jsonify({"estado": json.loads(fila[0]), "actualizado": fila[1]})
    except Exception as e:
        return jsonify({"error": "No se pudo leer: " + str(e)}), 500


@app.route("/datos", methods=["POST"])
def guardar_datos():
    try:
        cuerpo = request.get_json(force=True, silent=True) or {}
        if not pin_valido(cuerpo.get("pin")):
            return jsonify({"error": "PIN incorrecto."}), 403
        estado = cuerpo.get("estado")
        if estado is None:
            return jsonify({"error": "Falta 'estado'."}), 400
        actualizado = cuerpo.get("actualizado") or datetime.datetime.utcnow().isoformat()
        con = conexion()
        con.execute(
            "INSERT INTO estado (id, json, actualizado) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET json=excluded.json, actualizado=excluded.actualizado",
            (json.dumps(estado, ensure_ascii=False), actualizado),
        )
        con.commit()
        con.close()
        return jsonify({"ok": True, "actualizado": actualizado})
    except Exception as e:
        return jsonify({"error": "No se pudo guardar: " + str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
