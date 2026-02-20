from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

from models.database import init_db
from routes import templates_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

os.makedirs('template_images', exist_ok=True)

init_db()

app.register_blueprint(templates_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
