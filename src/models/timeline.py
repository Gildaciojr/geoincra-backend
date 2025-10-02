from src.models.user import db
from datetime import datetime

class Timeline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    stage = db.Column(db.String(100), nullable=False)  # Upload, OCR, Validação, etc
    status = db.Column(db.String(50), default='Pendente')  # Pendente, Em Andamento, Concluído
    progress = db.Column(db.Integer, default=0)  # 0-100
    notes = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Timeline {self.stage}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'stage': self.stage,
            'status': self.status,
            'progress': self.progress,
            'notes': self.notes,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
