from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.timeline import Timeline
from datetime import datetime

timeline_bp = Blueprint('timeline', __name__)

@timeline_bp.route('/api/timeline', methods=['GET'])
def get_timeline():
    project_id = request.args.get('project_id')
    if project_id:
        timeline = Timeline.query.filter_by(project_id=project_id).order_by(Timeline.created_at).all()
    else:
        timeline = Timeline.query.order_by(Timeline.created_at).all()
    return jsonify([item.to_dict() for item in timeline])

@timeline_bp.route('/api/timeline', methods=['POST'])
def create_timeline():
    data = request.json
    timeline = Timeline(
        project_id=data['project_id'],
        stage=data['stage'],
        status=data.get('status', 'Pendente'),
        progress=data.get('progress', 0),
        notes=data.get('notes')
    )
    db.session.add(timeline)
    db.session.commit()
    return jsonify(timeline.to_dict()), 201

@timeline_bp.route('/api/timeline/<int:timeline_id>', methods=['PUT'])
def update_timeline(timeline_id):
    timeline = Timeline.query.get_or_404(timeline_id)
    data = request.json
    
    if 'status' in data:
        timeline.status = data['status']
        if data['status'] == 'Em Andamento' and not timeline.started_at:
            timeline.started_at = datetime.utcnow()
        elif data['status'] == 'Concluído':
            timeline.completed_at = datetime.utcnow()
            timeline.progress = 100
    
    if 'progress' in data:
        timeline.progress = data['progress']
    if 'notes' in data:
        timeline.notes = data['notes']
    
    db.session.commit()
    return jsonify(timeline.to_dict())

@timeline_bp.route('/api/timeline/<int:timeline_id>', methods=['DELETE'])
def delete_timeline(timeline_id):
    timeline = Timeline.query.get_or_404(timeline_id)
    db.session.delete(timeline)
    db.session.commit()
    return '', 204
