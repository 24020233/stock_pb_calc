from flask import Blueprint, request, jsonify
from datetime import datetime, date
from services.pipeline_engine import PipelineEngine

bp = Blueprint('pipeline', __name__, url_prefix='/api/pipeline')

@bp.route('/status', methods=['GET'])
def get_status():
    day_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        day = datetime.strptime(day_str, '%Y-%m-%d').date()
        run = PipelineEngine.get_or_create_run(day)
        # Convert date/datetime objects to string for JSON serialization
        if run.get('day'):
             run['day'] = run['day'].strftime('%Y-%m-%d')
        if run.get('created_at'):
             run['created_at'] = run['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        if run.get('updated_at'):
             run['updated_at'] = run['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({"success": True, "data": run})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/run_node', methods=['POST'])
def run_node():
    data = request.get_json() or {}
    day_str = data.get('date') or datetime.now().strftime('%Y-%m-%d')
    node = data.get('node') # node_a, node_b, node_c, node_d
    
    try:
        day = datetime.strptime(day_str, '%Y-%m-%d').date()
        
        # Ensure run exists
        PipelineEngine.get_or_create_run(day)

        if node == 'node_a':
            PipelineEngine.run_node_a(day)
        elif node == 'node_b':
            PipelineEngine.run_node_b(day)
        elif node == 'node_c':
            PipelineEngine.run_node_c(day)
        elif node == 'node_d':
            PipelineEngine.run_node_d(day)
        else:
            return jsonify({"success": False, "error": "Invalid node"}), 400
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
