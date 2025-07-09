import requests
import os

# 🔐 TOKEN del bot (debes tenerlo en Railway como variable de entorno)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ✅ Lista de comunidades con sus respectivos grupos de Telegram
comunidades = [
    {"nombre": "brisas", "chat_id": "-123456789"},
    {"nombre": "miraflores", "chat_id": "-987654321"},
    {"nombre": "condores", "chat_id": "-111222333"},
    # Agrega más comunidades aquí...
]

# 🌐 Dominio base del servidor
BASE_URL = "https://alarma-production.up.railway.app"

# 🚀 Enviar botón a cada comunidad
for comunidad in comunidades:
    nombre = comunidad["nombre"]
    chat_id = comunidad["chat_id"]
    url_webapp = f"{BASE_URL}/?comunidad={nombre}"

    payload = {
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

    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json=payload
    )

    # 📋 Resultado
    if response.ok:
        print(f"✅ Botón enviado al grupo de {nombre}")
    else:
        print(f"❌ Error en {nombre}: {response.text}")
