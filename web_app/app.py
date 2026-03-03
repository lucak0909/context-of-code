from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
from web_app.blueprints.api import api_bp
from web_app.blueprints.reporting import reporting_bp

app = Flask(__name__)
CORS(app)

# Register Blueprints
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(reporting_bp, url_prefix="/api/report")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
