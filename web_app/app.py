from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from web_app.blueprints.api import api_bp
from web_app.blueprints.reporting import reporting_bp
from web_app.blueprints.auth import auth_bp
from common.utils.logging_setup import setup_logger

logger = setup_logger(__name__)

app = Flask(__name__)
logger.info("Flask app initialising")
CORS(app)

# Register Blueprints
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(reporting_bp, url_prefix="/api/report")
app.register_blueprint(auth_bp, url_prefix="/api/auth")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
