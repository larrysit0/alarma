import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.error import TelegramError

print("--- INICIO DEL SCRIPT ---")

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 🔐 TOKEN del bot y credenciales de Twilio (variables de entorno)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
WEBAPP_URL = os.getenv("WEBAPP_URL") # URL de tu aplicación en Railway

# 🏘️ Listado de chats de comunidades para comandos /sos
COMUNIDADES_CHATS = {
    "-1002585455176": "brisas",
    "-1002594518135": "mosca",
    "-1002886664361": "mosca2",
    "-1002773966470": "miraflores",
    "-1002780392932": "sos",
    "-1002735693923": "avion"
}

if not TELEGRAM_BOT_TOKEN or not WEBAPP_URL:
    print("--- ADVERTENCIA: Variables de entorno TELEGRAM_BOT_TOKEN o WEBAPP_URL NO están configuradas. ---")
    exit()

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None
    print("--- ADVERTENCIA: Variables de Twilio NO configuradas. Las llamadas no funcionarán. ---")

# Instancia del bot para usar en el webhook
bot = Bot(TELEGRAM_BOT_TOKEN)

# --- FUNCIONES AUXILIARES ---

def load_community_json(comunidad_nombre):
    filepath = os.path.join('comunidades', f"{comunidad_nombre.lower()}.json")
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

def make_phone_call(to_number, user_name, comunidad_nombre, descripcion, direccion):
    global twilio_client, TWILIO_PHONE_NUMBER
    if not twilio_client:
        return
    mensaje_voz = f"Alerta de emergencia. El usuario {user_name} activó una alarma en la comunidad {comunidad_nombre}. Descripción: {descripcion}. Dirección: {direccion}. Revisa tu celular para más detalles."
    response = VoiceResponse()
    response.say(mensaje_voz, voice='woman', language='es-ES')
    try:
        print(f"--- DEBUG: Haciendo llamada a {to_number} desde {TWILIO_PHONE_NUMBER} ---")
        call = twilio_client.calls.create(
            twiml=str(response),
            to=to_number,
            from_=TWILIO_PHONE_NUMBER
        )
        print(f"--- DEBUG: Llamada iniciada con SID: {call.sid} ---")
    except Exception as e:
        print(f"--- ERROR al hacer llamada a {to_number}: {e} ---")
        raise

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        # Aquí se convierte el objeto de ReplyMarkup a su representación JSON si es necesario
        payload["reply_markup"] = reply_markup.to_json()
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"--- Mensaje enviado exitosamente a {chat_id}. ---")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"--- ERROR al enviar mensaje a {chat_id}: {e} ---")
        return None

# --- RUTAS DE FLASK ---

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
    comunidad_info = load_community_json(comunidad)
    if comunidad_info:
        return jsonify(comunidad_info)
    return jsonify({}), 404

@app.route('/api/alert', methods=['POST'])
def handle_alert():
    print("--- Alerta recibida (POST). ---")
    data = request.json
    
    comunidad_nombre = data.get('comunidad')
    user_telegram = data.get('user_telegram', {})
    user_name = user_telegram.get('first_name', 'Anónimo')
    
    print(f"--- Alerta activada por: {user_name} en la comunidad: {comunidad_nombre} ---")

    if not comunidad_nombre:
        return jsonify({"error": "Nombre de comunidad no proporcionado"}), 400

    comunidad_info = load_community_json(comunidad_nombre)
    if not comunidad_info:
        return jsonify({"error": f"Comunidad '{comunidad_nombre}' no encontrada"}), 404

    chat_id = comunidad_info.get('chat_id')
    miembros = comunidad_info.get('miembros', [])

    if not chat_id:
        return jsonify({"error": "ID del chat de Telegram no configurado para esta comunidad"}), 500

    lat = data.get('ubicacion', {}).get('lat')
    lon = data.get('ubicacion', {}).get('lon')
    map_link = f"https://www.google.com/maps/place/{lat},{lon}" if lat and lon else "Ubicación no disponible"
    user_id = user_telegram.get('id', 'N/A')
    user_mention = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    
    tipo = data.get('tipo', 'Alerta no especificada')
    descripcion = data.get('descripcion', 'Sin descripción')
    direccion = data.get('direccion', 'Dirección no disponible')

    miembros_a_notificar = [m for m in miembros if m.get('alertas_activadas') and str(m.get('telegram_id')) != str(user_id)]
    
    if miembros_a_notificar:
        print("--- Enviando alertas privadas y llamadas a miembros... ---")
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
                numero_telefono = miembro.get('telefono')
                if numero_telefono:
                    print(f"--- DEBUG: Preparando llamada a {numero_telefono} ---")
                    try:
                        make_phone_call(numero_telefono, user_name, comunidad_nombre, descripcion, direccion)
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

@app.route('/api/register', methods=['POST'])
def register_id():
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        user_info = data.get('user_info', {})
        
        if telegram_id:
            print(f"--- DEBUG: ID de Telegram recibido para registro: {telegram_id} ---")
            print(f"--- DEBUG: Información de usuario: {user_info} ---")
            
            return jsonify({"status": "ID recibido y registrado."}), 200
        else:
            return jsonify({"error": "ID no proporcionado"}), 400
    except Exception as e:
        print(f"--- ERROR GENERAL en /api/register: {e} ---")
        return jsonify({"error": "Error interno del servidor"}), 500

# --- RUTA DEL WEBHOOK ---
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        
        message = update.message
        if not message:
            return "ok"

        text = message.text.upper().strip() if message.text else ""
        chat_id = str(message.chat_id)
        chat_type = message.chat.type
        user_data = message.from_user
        
        print(f"📥 Nuevo mensaje de @{user_data.username} en chat {chat_id} ({chat_type}): {text}")

        # Manejar el comando de registro en chat privado
        if text == "MIREGISTRO" and chat_type == "private":
            print(f"--- Comando 'MIREGISTRO' detectado. Enviando botón de registro. ---")
            webapp_url = f"{WEBAPP_URL}/register"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Obtener mi ID", web_app=WebAppInfo(url=webapp_url))]])
            
            try:
                bot.send_message(
                    chat_id, 
                    "Presiona el botón para obtener tu ID de Telegram y registrar tu interacción con el bot.", 
                    reply_markup=reply_markup
                )
            except TelegramError as e:
                print(f"--- ERROR al enviar mensaje de registro: {e} ---")

        # Manejar la palabra 'SOS' en chat de grupo
        elif text == "SOS" and chat_id in COMUNIDADES_CHATS:
            print(f"--- Comando 'SOS' detectado. Enviando botón de emergencia. ---")
            nombre_comunidad = COMUNIDADES_CHATS.get(chat_id)
            user_id = user_data.id
            user_first_name = user_data.first_name if user_data.first_name else ''
            user_last_name = user_data.last_name if user_data.last_name else ''
            user_username = user_data.username if user_data.username else ''
            
            url_webapp = f"{WEBAPP_URL}/?comunidad={nombre_comunidad}&id={user_id}&first_name={user_first_name}&last_name={user_last_name}&username={user_username}"
            
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚨🚨 ABRIR ALARMA VECINAL🚨🚨", web_app=WebAppInfo(url=url_webapp))]])
            
            try:
                bot.send_message(
                    chat_id, 
                    f"📣 VECINOS {nombre_comunidad.upper()}", 
                    reply_markup=reply_markup
                )
            except TelegramError as e:
                print(f"--- ERROR al enviar mensaje de emergencia: {e} ---")

        # Mensaje de bienvenida en chat privado
        elif text == "/START" and chat_type == "private":
            welcome_message = (
                "👋 ¡Hola! Soy el bot de alarmas vecinales. Para registrar tu interacción y poder recibir llamadas de emergencia, "
                "escribe el comando `MIREGISTRO` en este chat. "
                "Para activar una alarma en tu comunidad, escribe `SOS` en el grupo correspondiente."
            )
            try:
                bot.send_message(chat_id, welcome_message)
            except TelegramError as e:
                print(f"--- ERROR al enviar mensaje de bienvenida: {e} ---")

    return "ok"

# --- MAIN ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
