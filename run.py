import os
from app import criar_app

app = criar_app()

if __name__ == '__main__':
    app.run(host=os.getenv('SEPEX_HOST', '127.0.0.1'), port=int(os.getenv('SEPEX_PORT', '5000')))
