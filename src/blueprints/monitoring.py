import dataclasses
from flask import Blueprint, jsonify
from flask.views import MethodView
from src.monitor_model import DataCollector, MonitorReport

monitoring_bp = Blueprint('monitoring', __name__)

class MetricsAPI(MethodView):
    def get(self):
        collector = DataCollector()
        device_info = collector.get_device_info()
        metrics = collector.get_system_metrics()
        report = MonitorReport(device_info=device_info, metrics=metrics)
        return jsonify(dataclasses.asdict(report))

monitoring_bp.add_url_rule('/metrics', view_func=MetricsAPI.as_view('metrics_api'))
"""
"when /metrics is requested, run the get method of the MetricsAPI class"
the `as_view function converts the MetricsAPI class into a function flask can understand.`
"""