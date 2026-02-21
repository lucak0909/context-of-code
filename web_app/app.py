from flask import Flask
from web_app.blueprints.monitoring import monitoring_bp
from web_app.blueprints.api import api_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(monitoring_bp)
app.register_blueprint(api_bp, url_prefix="/api")

if __name__ == '__main__':
    app.run(debug=True)
