from src.models.user import db

class Confrontante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(14))
    spouse_name = db.Column(db.String(200))
    spouse_cpf = db.Column(db.String(14))
    address = db.Column(db.Text)
    property_name = db.Column(db.String(200))
    property_ccir = db.Column(db.String(50))
    property_matricula = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<Confrontante {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'cpf': self.cpf,
            'spouse_name': self.spouse_name,
            'spouse_cpf': self.spouse_cpf,
            'address': self.address,
            'property_name': self.property_name,
            'property_ccir': self.property_ccir,
            'property_matricula': self.property_matricula
        }
