import requests
import time

TELEGRAM_BOT_TOKEN = "TU_TOKEN_AQUI"

def obtener_chat_ids():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    data = response.json()

    print("🔁 Resultados de Telegram:")
    for update in data.get("result", []):
        msg = update.get("message") or update.get("edited_message")
        if msg:
            chat = msg["chat"]
            text = msg.get("text", "")
            print(f"🆔 Chat ID: {chat['id']} | Nombre: {chat.get('title', 'privado')} | Texto: {text}")

if __name__ == "__main__":
    while True:
        obtener_chat_ids()
        time.sleep(5)
