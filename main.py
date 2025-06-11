from flask import Flask, send_from_directory
from api.rotas_api import rotas_api
import os

app = Flask(__name__, static_folder="interface", static_url_path="/interface")
app.register_blueprint(rotas_api)

# 🔹 Rota principal (abre a interface)
@app.route("/")
def index():
    return send_from_directory("interface", "index.html")

# 🔹 Servir CSS e JS
@app.route("/<path:arquivo>")
def arquivos_estaticos(arquivo):
    return send_from_directory("interface", arquivo)

if __name__ == "__main__":
    print("🚀 Servidor iniciado em http://localhost:5000")
    app.run(debug=True, port=5000)
