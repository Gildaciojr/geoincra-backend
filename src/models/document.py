from src.models.user import db
from datetime import datetime

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    document_type = db.Column(db.String(100))  # matricula, escritura, etc
    file_name = db.Column(db.String(200))
    file_path = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Pendente')  # Pendente, Processado, Validado
    extracted_data = db.Column(db.Text)  # JSON com dados extraídos por OCR
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.file_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'status': self.status,
            'extracted_data': self.extracted_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
