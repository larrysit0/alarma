import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app) # Permite solicitudes de cualquier origen, importante para la Web App

# 🔐 TOKEN del bot (configurado como variable de entorno en Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Directorio donde se encuentran tus archivos JSON individuales de comunidades
COMUNIDADES_DIR = 'comunidades'

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# Función auxiliar para cargar un JSON de comunidad específico
def load_community_json(comunidad_nombre):
    filepath = os.path.join(COMUNIDADES_DIR, f"{comunidad_nombre.lower()}.json")
    if not os.path.exists(filepath):
        print(f"❌ Error: Archivo JSON no encontrado para la comunidad '{comunidad_nombre}' en '{filepath}'.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            comunidad_info = json.load(f)
            # Validar que el JSON cargado tenga la estructura esperada
            if isinstance(comunidad_info, dict) and "telegram_chat_id" in comunidad_info and "miembros" in comunidad_info:
                print(f"✅ Comunidad '{comunidad_nombre}' cargada desde '{filepath}'.")
                return comunidad_info
            else:
                print(f"⚠️ Advertencia: '{filepath}' no parece ser un JSON de comunidad válido.")
                return None
    except json.JSONDecodeError:
        print(f"❌ Error: '{filepath}' tiene un formato JSON inválido.")
        return None
    except Exception as e:
        print(f"❌ Error al cargar '{filepath}': {e}")
        return None

# Esta ruta ahora devuelve el OBJETO COMPLETO de la comunidad (solo miembros y chat_id)
@app.route('/api/comunidad/<comunidad>', methods=['GET'])
def get_comunidad_data(comunidad):
    comunidad_info = load_community_json(comunidad)
    if comunidad_info:
        return jsonify(comunidad_info)
    return jsonify({}), 404 # Devuelve un objeto vacío y 404 si la comunidad no se encuentra

@app.route('/api/alert', methods=['POST'])
def handle_alert():
    data = request.json
    print("📦 Datos recibidos para la alerta:", data)

    tipo = data.get('tipo', 'Alerta')
    descripcion = data.get('descripcion', 'Sin descripción')
    ubicacion_lat = data.get('ubicacion', {}).get('lat')
    ubicacion_lon = data.get('ubicacion', {}).get('lon')
    direccion = data.get('direccion', 'Dirección no disponible') # Esta es la dirección que llega desde script.js
    comunidad_nombre = data.get('comunidad')
    user_telegram = data.get('user_telegram', {})

    emisor_id = user_telegram.get('id', 'Desconocido')
    emisor_nombre = user_telegram.get('first_name', 'Anónimo')
    emisor_username = user_telegram.get('username', '')
    
    # Cargar la información de la comunidad que activó la alerta
    comunidad_info = load_community_json(comunidad_nombre)

    if not comunidad_info:
        print(f"❌ Error: Comunidad '{comunidad_nombre}' no encontrada o JSON inválido para alerta.")
        return jsonify({"status": "Error: Comunidad no configurada para alertas"}), 400

    chat_id_grupo = comunidad_info.get("telegram_chat_id")
    miembros_grupo = comunidad_info.get("miembros", [])
    
    if not chat_id_grupo:
        print(f"❌ Error: Chat ID de Telegram no encontrado en el JSON para la comunidad: {comunidad_nombre}")
        return jsonify({"status": "Error: Comunidad no tiene Chat ID configurado"}), 400


    mensaje = f"🚨 *¡ALERTA ROJA EN {comunidad_nombre.upper()}!* 🚨\n\n"
    mensaje += f"*Emitida por:* {emisor_nombre} ({'@' + emisor_username if emisor_username else 'ID:' + str(emisor_id)})\n"
    mensaje += f"*Descripción:* {descripcion}\n"
    if direccion != "Dirección no disponible":
        mensaje += f"*Dirección:* {direccion}\n"
    if ubicacion_lat and ubicacion_lon:
        mensaje += f"*Ubicación:* [Ver en Mapa](https://www.google.com/maps/search/?api=1&query={ubicacion_lat},{ubicacion_lon})"
    
    send_telegram_message(chat_id_grupo, mensaje, parse_mode='Markdown')

    for miembro in miembros_grupo:
        miembro_telegram_id = miembro.get('telegram_id')
        miembro_nombre = miembro.get('nombre')

        if miembro_telegram_id and str(miembro_telegram_id) != str(emisor_id):
            print(f"📤 Notificando a miembro: {miembro_nombre} (ID: {miembro_telegram_id})")
            mensaje_miembro = f"🚨 *Alerta de Vecino!* 🚨\n\n"
            mensaje_miembro += f"Tu vecino *{emisor_nombre}* ha activado una alerta en {comunidad_nombre.upper()}:\n"
            mensaje_miembro += f"Descripción: {descripcion}\n"
            if direccion != "Dirección no disponible":
                mensaje_miembro += f"Dirección: {direccion}\n"
            if ubicacion_lat and ubicacion_lon:
                mensaje_miembro += f"Ubicación: [Ver en Mapa](https://www.google.com/maps/search/?api=1&query={ubicacion_lat},{ubicacion_lon})"
            
            send_telegram_message(miembro_telegram_id, mensaje_miembro, parse_mode='Markdown')
            
    return jsonify({"status": f"Alerta enviada a la comunidad {comunidad_nombre}"})

def send_telegram_message(chat_id, text, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"✅ Mensaje enviado a {chat_id} (Telegram).")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al enviar mensaje a Telegram {chat_id}: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv("PORT", 8000))
