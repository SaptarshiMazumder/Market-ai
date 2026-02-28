from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

from routes import video_bp
from services.db import init_db

load_dotenv()

app = Flask(__name__)
CORS(app)

os.makedirs('videos', exist_ok=True)

init_db()
app.register_blueprint(video_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True)
