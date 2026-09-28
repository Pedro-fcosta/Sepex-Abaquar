import logging
import os
import secrets
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask


def criar_app(configuracao=None):
    app = Flask(__name__)
    raiz = Path(__file__).resolve().parent.parent
    app.config.update(
        SECRET_KEY=os.getenv('SEPEX_SECRET_KEY') or secrets.token_hex(32),
        DATABASE=str(raiz / os.getenv('SEPEX_DATABASE', 'instance/sepex.sqlite3')),
        ADMIN_TOKEN=os.getenv('SEPEX_ADMIN_TOKEN', ''),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    )
    if configuracao:
        app.config.update(configuracao)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    from .db import fechar_conexao
    app.teardown_appcontext(fechar_conexao)
    from .web import bp
    app.register_blueprint(bp)
    from .cli import registrar_comandos
    registrar_comandos(app)
    if not app.testing:
        arquivo = RotatingFileHandler(Path(app.config['DATABASE']).parent / 'sepex.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')
        arquivo.setLevel(logging.ERROR)
        app.logger.addHandler(arquivo)
    return app
