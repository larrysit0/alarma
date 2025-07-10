# 📦 Librerías necesarias
import os
import requests
import time
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

# 🌐 Configuración de entorno
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
BASE_URL = "https://alarma-production.up.railway.app"
DATA_FILE = os.path.join(os.path.dirname(__file__), 'comunidades')

# 📋 Diccionario de comunidades para botones
comunidades = {
    "-1002585455176": "brisas",
    "-987654321": "miraflores",
    "-111222333": "condores"
}

# 📤 Enviar botón WebApp a Telegram
def enviar_boton(chat_id, nombre):
    url_webapp = f"{BASE_URL}/?comunidad={nombre}"
    payload = {
        "chat_id": chat_id,
        "text": f"🚨 Abre la alarma de la comunidad: {nombre.upper()}",
        "reply_markup": {
            "keyboard": [[{
                "text": "🚨 ABRIR ALARMA VECINAL",
                "web_app": {"url": url_webapp}
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
    }
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json=payload
    )
    if response.ok:
        print(f"✅ Botón actualizado para {nombre}")
    else:
        print(f"❌ Error al enviar botón para {nombre}: {response.text}")

# 📥 Escucha actualizaciones de Telegram
def obtener_actualizaciones(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    response = requests.get(url, params=params)
    return response.json()

# 🧠 Hilo que mantiene el botón activo en los grupos
import threading
def iniciar_botones_telegram():
    def loop():
        last_update_id = None
        while True:
            data = obtener_actualizaciones(last_update_id)
            for update in data.get("result", []):
                last_update_id = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if not message:
                    continue
                chat = message.get("chat", {})
                chat_id = str(chat.get("id"))
                if chat_id in comunidades:
                    nombre = comunidades[chat_id]
                    enviar_boton(chat_id, nombre)
            time.sleep(2)
    threading.Thread(target=loop, daemon=True).start()

# 🌐 Servidor Flask
app = Flask(__name__)
CORS(app)
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/comunidades')
def listar_comunidades():
    comunidades_list = []
    for archivo in os.listdir(DATA_FILE):
        if archivo.endswith('.json'):
            comunidades_list.append(archivo.replace('.json', ''))
    return jsonify(comunidades_list)

@app.route('/api/ubicaciones/<comunidad>')
def ubicaciones_de_comunidad(comunidad):
    path = os.path.join(DATA_FILE, f"{comunidad}.json")
    if not os.path.exists(path):
        return jsonify({"error": "Comunidad no encontrada"}), 404
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data.get("miembros", []) if isinstance(data, dict) else data)

@app.route('/api/alert', methods=['POST'])
def recibir_alerta():
    data = request.get_json()
    print("📦 Datos recibidos:", data)

    tipo = data.get('tipo')
    descripcion = data.get('descripcion')
    ubicacion = data.get('ubicacion', {})
    direccion = data.get('direccion')
    comunidad = data.get('comunidad')

    lat = ubicacion.get('lat')
    lon = ubicacion.get('lon')

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

<b>Comunidad:</b> {comunidad.upper()}
<b>Dirección:</b> {direccion}
<b>Descripción:</b> {descripcion}
<b>Ubicación:</b> {lat}, {lon}
<b>🕐 Hora:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    enviar_telegram(telegram_chat_id, mensaje)

    for miembro in miembros:
        telefono = miembro.get('telefono')
        if not telefono:
            continue
        try:
            client.calls.create(
                twiml='<Response><Say voice="alice" language="es-ES">Emergencia. Alarma vecinal. Revisa tu celular.</Say></Response>',
                from_=TWILIO_FROM_NUMBER,
                to=telefono
            )
            print(f"📞 Llamada iniciada a {telefono}")
        except Exception as e:
            print(f"❌ Error al llamar a {telefono}: {e}")

    return jsonify({'status': f'Alerta enviada a la comunidad {comunidad}'}), 200

# 📤 Función para enviar mensajes a Telegram
def enviar_telegram(chat_id, mensaje):
    if not chat_id:
        print("❌ No se encontró chat_id de Telegram para esta comunidad.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
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

# ▶️ Iniciar tanto servidor como proceso de escucha de Telegram
if __name__ == '__main__':
    iniciar_botones_telegram()
    app.run(host='0.0.0.0', port=8000)
