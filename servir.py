"""Servidor para acesso por outros dispositivos na rede local ou pela internet."""

import os

from waitress import serve

from app import criar_app


def main():
    app = criar_app()
    serve(
        app,
        host=os.getenv('SEPEX_HOST', '0.0.0.0'),
        port=int(os.getenv('SEPEX_PORT', '5000')),
        threads=8,
    )


if __name__ == '__main__':
    main()
