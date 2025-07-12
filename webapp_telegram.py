import os
import requests
import time

# 🔑 Token del bot (asegúrate que esté en tus variables de entorno en Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 🌐 URL base de tu aplicación web para los botones
BASE_URL = "https://alarma-production.up.railway.app"

# 📋 Diccionario de comunidades conocidas (puedes agregar más luego)
comunidades = {
    "-1002585455176": "brisas",
    "-987654321": "miraflores",
    "-111222333": "condores"
}

# 📤 Envía un botón Web App al grupo correspondiente
def enviar_boton(chat_id, nombre):
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
    if response.ok:
        print(f"✅ Botón actualizado para {nombre}")
    else:
        print(f"❌ Error al enviar botón para {nombre}: {response.text}")

# 📡 Obtiene actualizaciones (mensajes nuevos que recibe el bot)
def obtener_actualizaciones(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    response = requests.get(url, params=params)
    return response.json()

# 🚀 Función principal: escucha mensajes y responde
def main():
    last_update_id = None
    while True:
        data = obtener_actualizaciones(last_update_id)
        for update in data.get("result", []):
            last_update_id = update["update_id"] + 1

            # 📩 Obtiene el mensaje (nuevo o editado)
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue

            # 🧾 Extrae el chat (grupo o usuario)
            chat = message.get("chat", {})
            chat_id = str(chat.get("id"))
            nombre_grupo = chat.get("title", "Privado o Sin Nombre")

            # 🖨️ Muestra el ID del grupo por consola (Railway logs)
            print(f"🆔 chat_id detectado: {chat_id} | Nombre: {nombre_grupo}")

            # 📌 Si el mensaje fue "/getid", responde directamente con el chat_id
            if message.get("text", "").strip().lower() == "/getid":
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": f"✅ Este es el chat_id del grupo *{nombre_grupo}*:\n\n`{chat_id}`",
                        "parse_mode": "Markdown"
                    }
                )

            # ✅ Si el grupo ya está en comunidades, envía el botón Web App
            if chat_id in comunidades:
                nombre = comunidades[chat_id]
                enviar_boton(chat_id, nombre)

        # ⏱ Espera un poco antes de seguir escuchando (para evitar saturación)
        time.sleep(2)

# ▶️ Inicia el proceso
if __name__ == "__main__":
    main()
