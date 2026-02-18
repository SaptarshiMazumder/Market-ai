from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

from config import UPLOAD_FOLDER, GENERATED_FOLDER, TEMPLATE_IMAGES_FOLDER
from models.database import init_db
from routes.training import training_bp
from routes.templates import templates_bp
from routes.generate import generate_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_IMAGES_FOLDER, exist_ok=True)

init_db()

app.register_blueprint(training_bp)
app.register_blueprint(templates_bp)
app.register_blueprint(generate_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
