import requests

TOKEN = "TU_TOKEN_NUEVO_BOT"
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

response = requests.get(url)
print(response.json())
