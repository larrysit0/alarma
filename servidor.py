from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # <-- Importa esto

app = Flask(__name__)

# Ruta principal: carga la WebApp
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para recibir la alerta
@app.route('/api/alert', methods=['POST'])
def recibir_alerta():
    data = request.get_json()
    print("📦 Datos recibidos:", data)

    if not data:
        return jsonify({'error': 'Falta el cuerpo del mensaje'}), 400

    tipo = data.get('tipo')
    descripcion = data.get('descripcion')
    ubicacion = data.get('ubicacion', {})

    lat = ubicacion.get('lat')
    lon = ubicacion.get('lon')

    print("📌 Tipo:", tipo)
    print("📝 Descripción:", descripcion)
    print("📍 Coordenadas:", lat, lon)

    if not descripcion or not lat or not lon:
        return jsonify({'error': 'Faltan datos'}), 400

    print("✅ Alerta recibida correctamente")

    return jsonify({'status': 'Alerta recibida correctamente'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
