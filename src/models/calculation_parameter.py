from src.models.user import db

class CalculationParameter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    min_area = db.Column(db.Float, nullable=False)
    max_area = db.Column(db.Float, nullable=False)
    price_per_hectare = db.Column(db.Float, nullable=False)
    minimum_price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<CalculationParameter {self.min_area}-{self.max_area}ha>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'min_area': self.min_area,
            'max_area': self.max_area,
            'price_per_hectare': self.price_per_hectare,
            'minimum_price': self.minimum_price,
            'description': self.description
        }
