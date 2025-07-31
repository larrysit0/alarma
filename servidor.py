import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

print("--- DEBUG: servidor.py: INICIO DEL SCRIPT ---") # <--- AÑADIDO

app = Flask(__name__, static_folder='static')
CORS(app) # Permite solicitudes de cualquier origen, importante para la Web App

print("--- DEBUG: servidor.py: Instancia de Flask creada ---") # <--- AÑADIDO

# 🔐 TOKEN del bot (configurado como variable de entorno en Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("--- DEBUG: ADVERTENCIA: TELEGRAM_BOT_TOKEN NO está configurado. Esto podría causar problemas. ---") # <--- AÑADIDO
else:
    print("--- DEBUG: TELEGRAM_BOT_TOKEN detectado. ---") # <--- AÑADIDO

# Directorio donde se encuentran tus archivos JSON individuales de comunidades
COMUNIDADES_DIR = 'comunidades'
print(f"--- DEBUG: COMUNIDADES_DIR establecida a: {COMUNIDADES_DIR} ---") # <--- AÑADIDO


# Ruta de verificación de salud (HEALTH CHECK)
@app.route('/healthz') # <--- AÑADIDO ESTA RUTA
def health_check():
    print("--- DEBUG: Ruta /healthz fue accedida. Retornando OK. ---")
    return "OK", 200


@app.route('/')
def index():
    print("--- DEBUG: Ruta / fue accedida. Sirviendo index.html. ---") # <--- AÑADIDO
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    print(f"--- DEBUG: Ruta /static/{filename} fue accedida. ---") # <--- AÑADIDO
    return send_from_directory(app.static_folder, filename)

# Función auxiliar para cargar un JSON de comunidad específico
def load_community_json(comunidad_nombre):
    print(f"--- DEBUG: Intentando cargar JSON para la comunidad: {comunidad_nombre} ---") # <--- AÑADIDO
    filepath = os.path.join(COMUNIDADES_DIR, f"{comunidad_nombre.lower()}.json")
    if not os.path.exists(filepath):
        print(f"--- DEBUG: Archivo JSON NO encontrado: {filepath} ---") # <--- AÑADIDO
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            comunidad_info = json.load(f)
            print(f"--- DEBUG: JSON para '{comunidad_nombre}' cargado exitosamente desde '{filepath}'. ---") # <--- AÑADIDO
            return comunidad_info
    except json.JSONDecodeError as e:
        print(f"--- DEBUG: ERROR JSONDecodeError para '{filepath}': {e} ---") # <--- Muestra el error JSON
        return None
    except Exception as e:
        print(f"--- DEBUG: ERROR General al cargar '{filepath}': {e} ---") # <--- Muestra cualquier otro error
        return None

# Esta ruta ahora devuelve el OBJETO COMPLETO de la comunidad (solo miembros y chat_id)
@app.route('/api/comunidad/<comunidad>', methods=['GET'])
def get_comunidad_data(comunidad):
    print(f"--- DEBUG: Ruta /api/comunidad/{comunidad} fue accedida. ---") # <--- AÑADIDO
    comunidad_info = load_community_json(comunidad)
    if comunidad_info:
        return jsonify(comunidad_info)
    return jsonify({}), 404 # Devuelve un objeto vacío y 404 si la comunidad no se encuentra

@app.route('/api/alert', methods=['POST'])
def handle_alert():
    print("--- DEBUG: Ruta /api/alert fue accedida (POST). ---") # <--- AÑADIDO
    data = request.json
    print("--- DEBUG: Datos recibidos para la alerta:", data) # <--- AÑADIDO

    # ... (el resto de tu código de handle_alert) ...

    # Final de handle_alert
    print(f"--- DEBUG: Finalizando handle_alert. Status: Alerta enviada a la comunidad {comunidad_nombre} ---")
    return jsonify({"status": f"Alerta enviada a la comunidad {comunidad_nombre}"})

def send_telegram_message(chat_id, text, parse_mode='HTML'):
    print(f"--- DEBUG: Intentando enviar mensaje a Telegram para chat_id: {chat_id} ---") # <--- AÑADIDO
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"--- DEBUG: Mensaje enviado exitosamente a {chat_id} (Telegram). ---") # <--- AÑADIDO
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"--- DEBUG: ERROR al enviar mensaje a Telegram {chat_id}: {e} ---") # <--- AÑADIDO
        return None
