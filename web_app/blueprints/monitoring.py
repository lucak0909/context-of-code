import dataclasses
from flask import Blueprint, jsonify
from flask.views import MethodView
from agent.pc_data_collector.collector import DataCollector, MonitorReport

monitoring_bp = Blueprint('monitoring', __name__)

collector = DataCollector()

def build_report_dict():
    # Use the global collector instance
    metrics = collector.get_network_metrics()
    report = MonitorReport(network_metrics=metrics)
    return dataclasses.asdict(report)

@monitoring_bp.route('/')
def monitoring_root():
    return jsonify(build_report_dict())

# Template example of how to add another route:
# class MetricsAPI(MethodView):
#     def get(self):
#         return jsonify(build_report_dict())

# monitoring_bp.add_url_rule('/metrics', view_func=MetricsAPI.as_view('metrics_api'))
# """
# "when /metrics is requested, run the get method of the MetricsAPI class"
# the `as_view function converts the MetricsAPI class into a function flask can understand.`
# """
