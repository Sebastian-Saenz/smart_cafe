from flask import Flask, jsonify, render_template
from flask_cors import CORS
from config import Config
from extensions import db, jwt, pool, test_PostgreSQL, test_Elasticsearch, test_Pool
import os
from routes.client import client_bp


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.config.from_object(Config)

    # 1. Configurando CORS
    CORS(app)

    # 2. Inicializar extensiones
    db.init_app(app)
    jwt.init_app(app)

    # 3. Registrar blueprints
    app.register_blueprint(client_bp, url_prefix="/client")

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    config = Config()
    test_PostgreSQL()
    test_Elasticsearch()
    test_Pool()
    app.run(host="0.0.0.0", port=8080)
