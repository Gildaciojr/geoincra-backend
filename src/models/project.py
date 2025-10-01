from src.models.user import db
from datetime import datetime

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Em Andamento')
    area_hectares = db.Column(db.Float)
    owner_name = db.Column(db.String(200))
    owner_cpf = db.Column(db.String(14))
    property_ccir = db.Column(db.String(50))
    property_matricula = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'area_hectares': self.area_hectares,
            'owner_name': self.owner_name,
            'owner_cpf': self.owner_cpf,
            'property_ccir': self.property_ccir,
            'property_matricula': self.property_matricula,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id
        }
