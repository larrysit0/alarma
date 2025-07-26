from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from datetime import datetime
import os
import json
import requests

# 📦 Twilio para llamadas
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__)
CORS(app)

# 📁 Carpeta con los datos de las comunidades
DATA_FILE = os.path.join(os.path.dirname(__file__), 'comunidades')

# 🔑 Credenciales Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')

# 🤖 Token de tu bot de Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# 🎯 Cliente Twilio
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# 🌐 Página principal
@app.route('/')
def index():
    return render_template('index.html')  # Debe estar en /templates

# 🔍 Lista de comunidades
@app.route('/api/comunidades')
def listar_comunidades():
    comunidades = []
    for archivo in os.listdir(DATA_FILE):
        if archivo.endswith('.json'):
            comunidades.append(archivo.replace('.json', ''))
    return jsonify(comunidades)

# 📍 Ubicaciones de una comunidad
@app.route('/api/ubicaciones/<comunidad>')
def ubicaciones_de_comunidad(comunidad):
    path = os.path.join(DATA_FILE, f"{comunidad}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Comunidad no encontrada"}), 404
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        return jsonify(data.get("miembros", []))
    else:
        return jsonify(data)

# 🚨 Alerta roja (se recibe desde el JS del botón)
@app.route('/api/alert', methods=['POST'])
def recibir_alerta():
    data = request.get_json()
    print("📦 Datos recibidos:", data)

    tipo = data.get('tipo')
    descripcion = data.get('descripcion')
    ubicacion = data.get('ubicacion', {})
    direccion = data.get('direccion')
    comunidad = data.get('comunidad')
    user_telegram = data.get('user_telegram', {})

    lat = ubicacion.get('lat')
    lon = ubicacion.get('lon')

    user_id = user_telegram.get('id', 'Desconocido')
    user_first_name = user_telegram.get('first_name', 'Desconocido')
    user_last_name = user_telegram.get('last_name', '')
    user_username = user_telegram.get('username', '')

    nombre_completo_usuario = f"{user_first_name} {user_last_name}".strip()
    if user_username:
        nombre_completo_usuario += f" (@{user_username})"
    else:
        nombre_completo_usuario += f" (ID: {user_id})"

    if not descripcion or not lat or not lon or not comunidad:
        return jsonify({'error': 'Faltan datos'}), 400

    archivo_comunidad = os.path.join(DATA_FILE, f"{comunidad}.json")
    if not os.path.exists(archivo_comunidad):
        return jsonify({'error': 'Comunidad no encontrada'}), 404

    with open(archivo_comunidad, 'r', encoding='utf-8') as f:
        datos_comunidad = json.load(f)

    miembros = datos_comunidad.get('miembros', [])
    telegram_chat_id = datos_comunidad.get('telegram_chat_id')

    mensaje = f"""
🚨 <b>ALERTA VECINAL</b> 🚨

<b>Activada por:</b> {nombre_completo_usuario}
<b>Comunidad:</b> {comunidad.upper()}
<b>Dirección:</b> {direccion}
<b>Descripción:</b> {descripcion}
<b>Ubicación:</b> <a href="https://www.google.com/maps?q={lat},{lon}">Ver en Google Maps</a>
<b>🕐 Hora:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""

    enviar_telegram(telegram_chat_id, mensaje)

    for miembro in miembros:
        nombre = miembro.get('nombre')
        telefono = miembro.get('telefono')

        if not telefono:
            continue

        try:
            client.calls.create(
                twiml=f'<Response><Say voice="alice" language="es-ES">Emergencia. Alarma vecinal. Revisa tu celular. La alerta fue activada por {user_first_name}.</Say></Response>',
                from_=TWILIO_FROM_NUMBER,
                to=telefono
            )
            print(f"📞 Llamada iniciada a {telefono}")
        except Exception as e:
            print(f"❌ Error al llamar a {telefono}: {e}")

    return jsonify({'status': f'Alerta enviada a la comunidad {comunidad}'}), 200

def enviar_telegram(chat_id, mensaje):
    if not chat_id:
        print("❌ No se encontró chat_id de Telegram para esta comunidad.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload)
        if response.ok:
            print(f"✅ Mensaje Telegram enviado al grupo {chat_id}")
        else:
            print(f"❌ Error Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Excepción al enviar mensaje Telegram: {e}")

@app.route('/twilio-voice', methods=['POST'])
def twilio_voice():
    response = VoiceResponse()
    response.say("Emergencia. Alarma vecinal. Revisa tu celular.", voice='alice', language='es-ES')
    return Response(str(response), mimetype='application/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
