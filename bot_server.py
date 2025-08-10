import os
import requests
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from twilio.rest import Client
from datetime import datetime
from telegram import Update, WebAppInfo
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
# Se utilizan para obtener las credenciales de forma segura
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
REGISTER_WEBAPP_URL = os.getenv("REGISTER_WEBAPP_URL")

# Variables de Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# --- VALIDACIÓN DE VARIABLES DE ENTORNO ---
if not all(
    [
        TELEGRAM_BOT_TOKEN,
        WEBAPP_URL,
        REGISTER_WEBAPP_URL,
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN,
        TWILIO_PHONE_NUMBER,
    ]
):
    print(
        "--- ADVERTENCIA: Variables de entorno TELEGRAM_BOT_TOKEN, WEBAPP_URL, REGISTER_WEBAPP_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER NO están configuradas. ---"
    )
    # Detener la ejecución si no se pueden obtener las variables críticas
    # Esto evita que el servidor se ejecute sin la configuración necesaria
    exit()
else:
    print("--- DEBUG: Todas las variables de entorno cargadas correctamente. ---")

# --- INSTANCIAS ---
flask_app = Flask(__name__, template_folder="templates")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# --- CONFIGURACIÓN DE DATOS DEL BOT ---
COMUNIDADES_CHATS = {
    # Aquí puedes agregar IDs de chat de grupos y supergrupos de Telegram
    "comunidad_ejemplo": {
        "chat_id": "-1002585455176",  # Reemplaza con el ID de tu grupo
        "miembros_telefono": [
            "+51987654321",  # Reemplaza con los números de teléfono de los miembros
        ],
    },
}

# Diccionario para almacenar los IDs de los usuarios que han interactuado con el bot
usuarios_registrados = {}


# --- FUNCIONES DEL BOT ---
def handle_text_message(update: Update, context: CallbackContext):
    """Maneja los mensajes de texto, incluyendo 'sos' sin la barra."""
    if update.message and update.message.text:
        message_text = update.message.text.lower().strip()
        chat_id = str(update.message.chat_id)

        print(
            f"📥 Nuevo mensaje de texto recibido en chat {chat_id}: '{message_text}'"
        )  # Log de depuración

        if message_text == "sos":
            print(
                f"🚨 Alerta 'sos' detectada en el chat {chat_id}. Procesando..."
            )  # Log de depuración
            handle_sos(update, context)
        else:
            # Puedes agregar lógica para otros comandos de texto aquí
            pass


def handle_sos(update: Update, context: CallbackContext):
    """
    Responde al comando /sos o al mensaje 'sos' con un botón que abre la web app.
    """
    chat_id = str(update.message.chat_id)
    print(f"✅ Comando /sos o 'sos' detectado en el chat: {chat_id}")

    # Verificar si el chat_id corresponde a una comunidad
    es_comunidad = any(
        comunidad["chat_id"] == chat_id
        for comunidad in COMUNIDADES_CHATS.values()
    )

    if es_comunidad:
        # Crea el botón que abrirá la web app
        reply_markup = {
            "inline_keyboard": [[{
                "text": "Activar Alarma",
                "web_app": {"url": WEBAPP_URL}
            }]]
        }
        
        try:
            context.bot.send_message(
                chat_id,
                "⚠️ Alerta recibida. Presiona el botón para activar la alarma. ⚠️",
                reply_markup=json.dumps(reply_markup)
            )
            print("➡️ Mensaje de alerta enviado al grupo.")
        except Exception as e:
            print(f"❌ Error al enviar mensaje al grupo {chat_id}: {e}")
    else:
        print(f"❌ Comando 'sos' ignorado. No es un chat de comunidad.")


def handle_miregistro(update: Update, context: CallbackContext):
    """
    Maneja el comando /miregistro y envía un botón para abrir la web app de registro.
    """
    chat_id = update.message.chat_id
    
    print(
        f"✅ Comando /miregistro detectado del usuario {update.effective_user.id}"
    ) # Log de depuración

    reply_markup = {
        "inline_keyboard": [[{
            "text": "Obtener mi ID",
            "web_app": {"url": REGISTER_WEBAPP_URL}
        }]]
    }
    
    try:
        context.bot.send_message(
            chat_id,
            "Presiona el botón para obtener y registrar tu ID de Telegram.",
            reply_markup=json.dumps(reply_markup)
        )
        print("➡️ Mensaje de registro enviado.")
    except Exception as e:
        print(f"❌ Error al enviar mensaje de registro: {e}")


# --- RUTAS DE FLASK ---
@flask_app.route('/')
def index():
    return render_template('index.html')


@flask_app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@flask_app.route('/api/alert', methods=['POST'])
def handle_alert():
    try:
        data = request.json
        motivo = data.get('motivo', 'No especificado')
        chat_id_alerta = data.get('chat_id')

        print(f"🚨 Alerta recibida desde la web app. Motivo: {motivo}")

        # Enviar el mensaje de alerta al grupo
        if chat_id_alerta:
            mensaje_alerta = f"⚠️ ALERTA ⚠️\nMotivo: {motivo}\nHora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                updater.bot.send_message(
                    chat_id_alerta,
                    mensaje_alerta
                )
                print(f"✅ Mensaje de alerta enviado al grupo {chat_id_alerta}")
            except Exception as e:
                print(f"❌ Error al enviar mensaje al grupo: {e}")

        # Enviar la alerta a todos los miembros por teléfono
        for comunidad_id, comunidad_data in COMUNIDADES_CHATS.items():
            if comunidad_data["chat_id"] == chat_id_alerta:
                for telefono in comunidad_data["miembros_telefono"]:
                    try:
                        call = twilio_client.calls.create(
                            twiml='<Response><Say language="es-ES">Alerta de emergencia. Motivo: ' + motivo + '</Say></Response>',
                            to=telefono,
                            from_=TWILIO_PHONE_NUMBER
                        )
                        print(f"✅ Llamada iniciada a {telefono}. SID: {call.sid}")
                    except Exception as e:
                        print(f"❌ Error al iniciar llamada a {telefono}: {e}")

        return jsonify({"status": "Alerta procesada"}), 200

    except Exception as e:
        print(f"❌ Error en /api/alert: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@flask_app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), updater.bot)
        updater.dispatcher.process_update(update)
    return "ok"


# --- MAIN ---
if __name__ == "__main__":
    print("--- INICIO DEL SCRIPT ---")
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Handler para el comando /start (opcional)
    dispatcher.add_handler(CommandHandler('start', lambda update, context: update.message.reply_text("Hola, soy tu bot de alarma.")))

    # Handler para el comando /miregistro
    dispatcher.add_handler(CommandHandler('miregistro', handle_miregistro))

    # Handler para el mensaje 'sos' sin la barra
    dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))

    # Iniciar el servidor Flask para el webhook y la web app
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
