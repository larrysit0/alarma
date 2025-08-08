import os
import requests
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from twilio.rest import Client

print("--- DEBUG: servidor.py: INICIO DEL SCRIPT ---")

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

print("--- DEBUG: servidor.py: Instancia de Flask creada ---")

# 🔐 TOKEN del bot (configurado como variable de entorno en Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not TELEGRAM_BOT_TOKEN:
    print("--- DEBUG: ADVERTENCIA: TELEGRAM_BOT_TOKEN NO está configurado. ---")
else:
    print("--- DEBUG: TELEGRAM_BOT_TOKEN detectado. ---")

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    print("--- DEBUG: Cliente de Twilio inicializado. ---")
else:
    twilio_client = None
    print("--- DEBUG: ADVERTENCIA: Variables de Twilio NO configuradas. Las llamadas telefónicas no funcionarán. ---")

# Directorio donde se encuentran tus archivos JSON individuales de comunidades
COMUNIDADES_DIR = 'comunidades'
print(f"--- DEBUG: COMUNIDADES_DIR establecida a: {COMUNIDADES_DIR} ---")

@app.route('/healthz')
def health_check():
    print("--- DEBUG: Ruta /healthz fue accedida. Retornando OK. ---")
    return "OK", 200

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

    lat = ubicacion.get('lat')
    lon = ubicacion.get('lon')
    map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "Ubicación no disponible"

    user_name = user_telegram.get('first_name', 'Anónimo')
    user_id = user_telegram.get('id', 'N/A')
    user_mention = f"<a href='tg://user?id={user_id}'>{user_name}</a>"

    miembros_a_notificar = [m for m in miembros if m.get('alertas_activadas') and m.get('telegram_id') != user_id]
    
    # 🔔 LÓGICA DE NOTIFICACIONES TELEGRAM
    if miembros_a_notificar:
        print("--- DEBUG: Enviando alertas privadas a miembros de la comunidad. ---")
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
    
    # 📞 LÓGICA DE LLAMADAS TELEFÓNICAS
    if twilio_client and TWILIO_PHONE_NUMBER:
        print("--- DEBUG: Iniciando llamadas telefónicas. ---")
        for miembro in miembros_a_notificar:
            numero_telefono = miembro.get('telefono')
            if numero_telefono:
                print(f"--- DEBUG: Llamando a {numero_telefono} ---")
                try:
                    make_phone_call(numero_telefono, comunidad_nombre, user_name, tipo, descripcion)
                except Exception as e:
                    print(f"--- DEBUG: ERROR al hacer llamada a {numero_telefono}: {e} ---")

    # 🔔 MENSAJE DE CONFIRMACIÓN AL GRUPO
    mensaje_grupo = (
        f"<b>🚨 ALERTA ROJA ACTIVADA EN LA COMUNIDAD {comunidad_nombre.upper()}</b>\n"
        f"<b>Activada por:</b> {user_mention}\n"
        f"<b>Descripción:</b> {descripcion}\n"
        f"<b>Ubicación:</b> <a href='{map_link}'>Ver en Google Maps</a>\n"
        f"<b>Dirección:</b> {direccion}\n\n"
        f"ℹ️ Se han enviado notificaciones a los miembros registrados y se ha iniciado el protocolo de llamadas."
    )
    send_telegram_message(chat_id, mensaje_grupo)

    print(f"--- DEBUG: Finalizando handle_alert. Status: Alerta enviada a la comunidad {comunidad_nombre} ---")
    return jsonify({"status": f"Alerta enviada a la comunidad {comunidad_nombre}"})

# 📞 NUEVA FUNCIÓN PARA HACER LLAMADAS
def make_phone_call(to_number, comunidad, user, tipo, descripcion):
    global twilio_client, TWILIO_PHONE_NUMBER
    
    call_text = (
        f"Alerta de emergencia en la comunidad {comunidad}. "
        f"El usuario {user} ha activado una alerta roja. "
        f"El tipo de emergencia es {tipo} con la siguiente descripcion: {descripcion}."
    )
    
    twiml_url = f"http://twimlets.com/echo?Twiml=%3CResponse%3E%3CSay%20voice%3D%22woman%22%20language%3D%22es-ES%22%3E{requests.utils.quote(call_text)}%3C%2FSay%3E%3C%2FResponse%3E"

    call = twilio_client.calls.create(
        twiml=f'<Response><Say language="es-ES">Una alerta de emergencia ha sido activada en la comunidad {comunidad}.</Say></Response>',
        to=to_number,
        from_=TWILIO_PHONE_NUMBER
    )
    print(f"--- DEBUG: Llamada iniciada con SID: {call.sid} ---")

# 🔔 FUNCIONES DE TELEGRAM
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
