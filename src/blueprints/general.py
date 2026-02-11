from flask import Blueprint

general_bp = Blueprint('general', __name__)

@general_bp.route('/')
def hello_world():
    return "<p>Hello, World!</p>"
