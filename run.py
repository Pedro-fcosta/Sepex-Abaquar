import os
from app import criar_app

app = criar_app()

if __name__ == '__main__':
    app.run(host=os.getenv('SEPEX_HOST', '0.0.0.0'), port=int(os.getenv('SEPEX_PORT', '1234')))
