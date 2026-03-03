import os
from dotenv import load_dotenv
load_dotenv()  # must run before any module-level env reads (e.g. Gemini client init)

from flask import Flask
from flask_cors import CORS
from routes.image_generation import image_generation_bp
from routes.masking import masking_bp

app = Flask(__name__)
CORS(app)

os.makedirs('generated', exist_ok=True)
os.makedirs('masks', exist_ok=True)

app.register_blueprint(image_generation_bp)
app.register_blueprint(masking_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5008, debug=True)
