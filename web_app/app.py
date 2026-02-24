from flask import Flask, jsonify
from datetime import datetime, timezone
from web_app.blueprints.api import api_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(api_bp, url_prefix="/api")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
