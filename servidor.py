import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS

print("--- DEBUG: servidor.py: INICIO DEL SCRIPT ---")

app = Flask(__name__, static_folder='static', template_folder='templates') # Añadido template_folder
CORS(app)

print("--- DEBUG: servidor.py: Instancia de Flask creada ---")

# 🔐 TOKEN del bot (configurado como variable de entorno en Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("--- DEBUG: ADVERTENCIA: TELEGRAM_BOT_TOKEN NO está configurado. Esto podría causar problemas. ---")
else:
    print("--- DEBUG: TELEGRAM_BOT_TOKEN detectado. ---")

# Directorio donde se encuentran tus archivos JSON individuales de comunidades
COMUNIDADES_DIR = 'comunidades'
print(f"--- DEBUG: COMUNIDADES_DIR establecida a: {COMUNIDADES_DIR} ---")


# Ruta de verificación de salud (HEALTH CHECK)
@app.route('/healthz')
def health_check():
    print("--- DEBUG: Ruta /healthz fue accedida. Retornando OK. ---")
    return "OK", 200

# CORREGIDO: Usar render_template para procesar el HTML
@app.route('/')
def index():
    print("--- DEBUG: Ruta / fue accedida. Sirviendo index.html. ---")
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    print(f"--- DEBUG: Ruta /static/{filename} fue accedida. ---")
    return send_from_directory(app.static_folder, filename)

def load_community_json(comunidad_nombre):
    print(f"--- DEBUG: Intentando cargar JSON para la comunidad: {comunidad_nombre} ---")
    filepath = os.path.join(COMUNIDADES_DIR, f"{comunidad_nombre.lower()}.json")
    if not os.path.exists(filepath):
        print(f"--- DEBUG: Archivo JSON NO encontrado: {filepath} ---")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            comunidad_info = json.load(f)
            print(f"--- DEBUG: JSON para '{comunidad_nombre}' cargado exitosamente desde '{filepath}'. ---")
            return comunidad_info
    except json.JSONDecodeError as e:
        print(f"--- DEBUG: ERROR JSONDecodeError para '{filepath}': {e} ---")
        return None
    except Exception as e:
        print(f"--- DEBUG: ERROR General al cargar '{filepath}': {e} ---")
        return None

@app.route('/api/comunidad/<comunidad>', methods=['GET'])
def get_comunidad_data(comunidad):
    print(f"--- DEBUG: Ruta /api/comunidad/{comunidad} fue accedida. ---")
    comunidad_info = load_community_json(comunidad)
    if comunidad_info:
        return jsonify(comunidad_info)
    return jsonify({}), 404

@app.route('/api/alert', methods=['POST'])
def handle_alert():
    print("--- DEBUG: Ruta /api/alert fue accedida (POST). ---")
    data = request.json
    print("--- DEBUG: Datos recibidos para la alerta:", data)

    tipo = data.get('tipo', 'Alerta no especificada')
    descripcion = data.get('descripcion', 'Sin descripción')
    comunidad_nombre = data.get('comunidad')
    ubicacion = data.get('ubicacion', {})
    direccion = data.get('direccion', 'Dirección no disponible')
    user_telegram = data.get('user_telegram', {})

    if not comunidad_nombre:
        print("--- DEBUG: Error: 'comunidad' no se encuentra en los datos. ---")
        return jsonify({"error": "Nombre de comunidad no proporcionado"}), 400

    comunidad_info = load_community_json(comunidad_nombre)
    if not comunidad_info:
        print(f"--- DEBUG: Error: Comunidad '{comunidad_nombre}' no encontrada. ---")
        return jsonify({"error": f"Comunidad '{comunidad_nombre}' no encontrada"}), 404

    chat_id = comunidad_info.get('chat_id')
    miembros = comunidad_info.get('miembros', [])

    if not chat_id:
        print(f"--- DEBUG: Error: 'chat_id' no encontrado para la comunidad '{comunidad_nombre}'. ---")
        return jsonify({"error": "ID del chat de Telegram no configurado para esta comunidad"}), 500

    # Construir el mensaje de Telegram
    lat = ubicacion.get('lat')
    lon = ubicacion.get('lon')
    map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "Ubicación no disponible"

    user_name = user_telegram.get('first_name', 'Anónimo')
    user_id = user_telegram.get('id', 'N/A')
    user_mention = f"<a href='tg://user?id={user_id}'>{user_name}</a>"

    miembros_alertados = [m for m in miembros if m.get('alertas_activadas')]
    nombres_miembros = [m.get('nombre') for m in miembros_alertados]
    menciones_miembros = [f"<a href='tg://user?id={m.get('telegram_id')}'>{m.get('nombre')}</a>" for m in miembros_alertados]

    mensaje_alertas = " ".join(menciones_miembros)

    mensaje_completo = (
        f"<b>🚨 ALERTA ROJA 🚨</b>\n"
        f"<b>Tipo:</b> {tipo}\n"
        f"<b>Comunidad:</b> {comunidad_nombre.upper()}\n"
        f"<b>Usuario:</b> {user_mention}\n"
        f"<b>Descripción:</b> {descripcion}\n"
        f"<b>Ubicación:</b> <a href='{map_link}'>Ver en Google Maps</a>\n"
        f"<b>Dirección:</b> {direccion}\n\n"
        f"<b>Personas a las que se les notificó:</b> {mensaje_alertas}"
    )

    send_telegram_message(chat_id, mensaje_completo)

    print(f"--- DEBUG: Finalizando handle_alert. Status: Alerta enviada a la comunidad {comunidad_nombre} ---")
    return jsonify({"status": f"Alerta enviada a la comunidad {comunidad_nombre}"})

def send_telegram_message(chat_id, text, parse_mode='HTML'):
    print(f"--- DEBUG: Intentando enviar mensaje a Telegram para chat_id: {chat_id} ---")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"--- DEBUG: Mensaje enviado exitosamente a {chat_id} (Telegram). ---")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"--- DEBUG: ERROR al enviar mensaje a Telegram {chat_id}: {e} ---")
        return None

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"--- DEBUG: Iniciando servidor Flask en puerto {port} ---")
    app.run(host='0.0.0.0', port=port)
