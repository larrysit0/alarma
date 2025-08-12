import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

print("--- INICIO DEL SCRIPT ---")

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 🔐 TOKEN del bot y credenciales de Twilio (variables de entorno)
# ¡IMPORTANTE!: Asegúrate de que esta variable de entorno esté actualizada en Railway con el token de tu NUEVO bot.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not TELEGRAM_BOT_TOKEN:
    print("--- ADVERTENCIA: TELEGRAM_BOT_TOKEN NO está configurado. ---")

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None
    print("--- ADVERTENCIA: Variables de Twilio NO configuradas. Las llamadas no funcionarán. ---")

COMUNIDADES_DIR = 'comunidades'

def load_community_json(comunidad_nombre):
    filepath = os.path.join(COMUNIDADES_DIR, f"{comunidad_nombre.lower()}.json")
    if not os.path.exists(filepath):
        print(f"--- Archivo JSON NO encontrado: {filepath} ---")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            comunidad_info = json.load(f)
            return comunidad_info
    except Exception as e:
        print(f"--- ERROR al cargar '{filepath}': {e} ---")
        return None

def get_community_by_chat_id(chat_id):
    try:
        chat_id_str = str(chat_id)

        for filename in os.listdir(COMUNIDADES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(COMUNIDADES_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    comunidad_info = json.load(f)
                    
                    json_chat_id_str = str(comunidad_info.get('chat_id'))
                    
                    if json_chat_id_str == chat_id_str:
                        return filename.replace('.json', '')
    except Exception as e:
        print(f"--- ERROR al buscar comunidad por chat_id: {e} ---")
    return None

@app.route('/healthz')
def health_check():
    return "OK", 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/comunidad/<comunidad>', methods=['GET'])
def get_comunidad_data(comunidad):
    # Este endpoint se mantiene por si lo usas en otras partes.
    comunidad_info = load_community_json(comunidad)
    if comunidad_info:
        return jsonify(comunidad_info)
    return jsonify({}), 404

# --- NUEVO ENDPOINT PARA OBTENER LA COMUNIDAD POR CHAT_ID (para el frontend) ---
@app.route('/api/comunidad_por_chat/<chat_id>', methods=['GET'])
def get_comunidad_by_chat_id_api(chat_id):
    print(f"--- Solicitud API recibida para chat_id: {chat_id} ---")
    
    comunidad_nombre = get_community_by_chat_id(chat_id)
    if not comunidad_nombre:
        print(f"--- ADVERTENCIA: No se encontró la comunidad para el chat_id: {chat_id} ---")
        return jsonify({"error": "Comunidad no encontrada"}), 404

    comunidad_info = load_community_json(comunidad_nombre)
    if not comunidad_info:
        return jsonify({"error": "Datos de comunidad no encontrados"}), 404

    # Añade el nombre de la comunidad a la respuesta JSON
    comunidad_info['comunidad'] = comunidad_nombre
    
    print(f"--- Datos de la comunidad '{comunidad_nombre}' enviados. ---")
    return jsonify(comunidad_info)


@app.route('/api/alert', methods=['POST'])
def handle_alert():
    print("--- Alerta recibida (POST). ---")
    data = request.json
    
    # El script.js ahora envía 'chat_id' en lugar de 'comunidad'
    chat_id = data.get('chat_id')
    user_telegram = data.get('user_telegram', {})
    user_name = user_telegram.get('first_name', 'Anónimo')
    
    if not chat_id:
        return jsonify({"error": "ID del chat no proporcionado"}), 400
    
    # Busca el nombre de la comunidad usando el chat_id
    comunidad_nombre = get_community_by_chat_id(chat_id)
    if not comunidad_nombre:
        return jsonify({"error": f"Comunidad no encontrada para el chat_id '{chat_id}'"}), 404
    
    print(f"--- Alerta activada por: {user_name} en la comunidad: {comunidad_nombre} ---")

    comunidad_info = load_community_json(comunidad_nombre)
    if not comunidad_info:
        return jsonify({"error": f"Comunidad '{comunidad_nombre}' no encontrada"}), 404

    miembros = comunidad_info.get('miembros', [])

    lat = data.get('ubicacion', {}).get('lat')
    lon = data.get('ubicacion', {}).get('lon')
    map_link = f"http://maps.google.com/?q={lat},{lon}" if lat and lon else "Ubicación no disponible"
    user_id = user_telegram.get('id', 'N/A')
    user_mention = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    
    tipo = data.get('tipo', 'Alerta no especificada')
    descripcion = data.get('descripcion', 'Sin descripción')
    direccion = data.get('direccion', 'Dirección no disponible')

    miembros_a_notificar = [m for m in miembros if m.get('alertas_activadas') and str(m.get('telegram_id')) != str(user_id)]
    
    if miembros_a_notificar:
        print("--- Enviando alertas privadas a miembros... ---")
        for miembro in miembros_a_notificar:
            id_miembro = miembro.get('telegram_id')
            nombre_miembro = miembro.get('nombre', 'miembro')
            mensaje_privado = (
                f"<b>🚨 ALERTA DE EMERGENCIA 🚨</b>\n"
                f"<b>Tipo:</b> {tipo}\n"
                f"<b>Comunidad:</b> {comunidad_nombre.upper()}\n"
                f"<b>Usuario que activó la alarma:</b> {user_mention}\n"
                f"<b>Descripción:</b> {descripcion}\n"
                f"<b>Ubicación:</b> <a href='{map_link}'>Ver en Google Maps</a>\n"
                f"<b>Dirección:</b> {direccion}\n\n"
                f"¡{nombre_miembro}, por favor, revisa el grupo para más detalles!"
            )
            send_telegram_message(id_miembro, mensaje_privado)
    
    if twilio_client and TWILIO_PHONE_NUMBER:
        print("--- Iniciando llamadas telefónicas. ---")
        for miembro in miembros_a_notificar:
            numero_telefono = miembro.get('telefono')
            if numero_telefono:
                print(f"--- Llamando a un miembro de la comunidad: {numero_telefono} ---")
                try:
                    make_phone_call(numero_telefono)
                except Exception as e:
                    print(f"--- ERROR al hacer llamada: {e} ---")

    mensaje_grupo = (
        f"<b>🚨 ALERTA ROJA ACTIVADA EN LA COMUNIDAD {comunidad_nombre.upper()}</b>\n"
        f"<b>Activada por:</b> {user_mention}\n"
        f"<b>Descripción:</b> {descripcion}\n"
        f"<b>Ubicación:</b> <a href='{map_link}'>Ver en Google Maps</a>\n"
        f"<b>Dirección:</b> {direccion}\n\n"
        f"ℹ️ Se han enviado notificaciones a los miembros registrados y se ha iniciado el protocolo de llamadas."
    )
    send_telegram_message(chat_id, mensaje_grupo)

    print("--- Alerta procesada exitosamente. ---")
    return jsonify({"status": "Alerta enviada."})

def make_phone_call(to_number):
    global twilio_client, TWILIO_PHONE_NUMBER
    mensaje_voz = "Emergencia, revisa tu celular."
    response = VoiceResponse()
    response.say(mensaje_voz, voice='woman', language='es-ES')
    try:
        call = twilio_client.calls.create(
            twiml=str(response),
            to=to_number,
            from_=TWILIO_PHONE_NUMBER
        )
    except Exception:
        raise

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
        print(f"--- Mensaje enviado exitosamente a {chat_id}. ---")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"--- ERROR al enviar mensaje a {chat_id}: {e} ---")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.json
        message = update.get('message')
        if message:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            user_id = message['from']['id']
            user_name = message['from']['first_name']

            print(f"--- [DEBUG] Comando recibido: {text} ---")
            print(f"--- [DEBUG] chat_id del mensaje: {chat_id} ---")

            if text.upper() == 'MIREGISTRO':
                print(f"--- [MIREGISTRO] ID de Telegram de {user_name}: {user_id} ---")
                send_telegram_message(chat_id, f"Hola {user_name}, tu ID de Telegram ha sido registrado. Lo puedes encontrar en los logs del sistema.")
            
            elif text.upper() == 'SOS':
                comunidad_nombre = get_community_by_chat_id(chat_id)
                print(f"--- [DEBUG] Comunidad encontrada: {comunidad_nombre} ---")

                if comunidad_nombre:
                    # La URL del web_app ahora es solo la URL base con la barra final.
                    # ¡IMPORTANTE!: Asegúrate de que esta URL sea la misma que configuraste en BotFather.
                    url_base_webapp = 'https://alertaperu-production.up.railway.app/'
                    
                    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": f"🚨 {user_name} ha activado una emergencia. Presiona el botón para enviar una alerta roja.",
                        "reply_markup": {
                            "inline_keyboard": [
                                [
                                    {
                                        "text": "🚨 Enviar Alerta Roja",
                                        "web_app": { "url": url_base_webapp }
                                    }
                                ]
                            ]
                        }
                    }
                    try:
                        response = requests.post(url, json=payload)
                        response.raise_for_status()
                        print(f"--- Mensaje de WebApp enviado exitosamente a {chat_id}. ---")
                    except requests.exceptions.RequestException as e:
                        print(f"--- ERROR al enviar mensaje de WebApp a {chat_id}: {e} ---")
                else:
                    print(f"--- ADVERTENCIA: No se encontró la comunidad para el chat_id: {chat_id} ---")
                    send_telegram_message(chat_id, "Lo siento, no pude encontrar la comunidad asociada a este grupo. Por favor, asegúrate de que el bot está configurado para este chat.")
            
    except Exception as e:
        print(f"--- ERROR GENERAL en el webhook: {e} ---")
    
    return jsonify({"status": "ok"}), 200

@app.route('/api/register', methods=['POST'])
def register_id():
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        if telegram_id:
            return jsonify({"status": "ID recibido y registrado."}), 200
        else:
            return jsonify({"error": "ID no proporcionado"}), 400
    except Exception as e:
        return jsonify({"error": "Error interno del servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
