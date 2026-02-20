from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

from routes import generate_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

os.makedirs('uploads', exist_ok=True)
os.makedirs('generated', exist_ok=True)

app.register_blueprint(generate_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
