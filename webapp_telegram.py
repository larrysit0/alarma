import requests
import os

# 🔐 TOKEN del bot (debe estar configurado como variable de entorno en Railway o .env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ✅ Lista de comunidades con sus respectivos grupos de Telegram
comunidades = [
    {"nombre": "brisas", "chat_id": "-1002585455176"},
    {"nombre": "miraflores", "chat_id": "-987654321"},
    {"nombre": "condores", "chat_id": "-111222333"},
    # ➕ Agrega más comunidades según necesites...
]

# 🌐 URL base de tu WebApp (ajústala según tu dominio de producción)
BASE_URL = "https://alarma-production.up.railway.app"

# 🖼️ URL del logo o imagen de encabezado para acompañar el botón
LOGO_URL = "https://tuservidor.com/logo_alarma.jpg"  # Asegúrate que sea pública y accesible

# 🚀 Enviar WebApp + imagen a cada comunidad
for comunidad in comunidades:
    nombre = comunidad["nombre"]
    chat_id = comunidad["chat_id"]

    # 🔗 URL específica de la comunidad
    url_webapp = f"{BASE_URL}/?comunidad={nombre}"

    # 🖼️ Enviar imagen con mensaje destacado
    mensaje = f"""
🚨 <b>ALERTA VECINAL</b> 🚨

<b>Comunidad:</b> {nombre.upper()}
Pulsa el botón para acceder a la alarma vecinal de tu zona.
"""
    photo_payload = {
        "chat_id": chat_id,
        "photo": LOGO_URL,
        "caption": mensaje,
        "parse_mode": "HTML"
    }

    photo_response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
        json=photo_payload
    )

    if photo_response.ok:
        print(f"✅ Imagen enviada al grupo de {nombre}")
    else:
        print(f"❌ Error al enviar imagen en {nombre}: {photo_response.text}")

    # 🎛️ Enviar botón WebApp al grupo
    button_payload = {
        "chat_id": chat_id,
        "text": f"🚨 Abre la alarma de la comunidad: {nombre.upper()}",
        "reply_markup": {
            "keyboard": [[{
                "text": "🚨 ABRIR ALARMA VECINAL",
                "web_app": {
                    "url": url_webapp
                }
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
    }

    button_response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json=button_payload
    )

    if button_response.ok:
        print(f"✅ Botón enviado al grupo de {nombre}")
    else:
        print(f"❌ Error al enviar botón en {nombre}: {button_response.text}")
