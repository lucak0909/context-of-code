from flask import Flask
from src.blueprints.monitoring import monitoring_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(monitoring_bp)

if __name__ == '__main__':
    app.run(debug=True)
