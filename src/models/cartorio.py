from src.models.user import db

class Cartorio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    whatsapp = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<Cartorio {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'email': self.email,
            'whatsapp': self.whatsapp
        }
