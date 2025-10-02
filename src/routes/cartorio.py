from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.cartorio import Cartorio

cartorio_bp = Blueprint('cartorio', __name__)

@cartorio_bp.route('/api/cartorios', methods=['GET'])
def get_cartorios():
    state = request.args.get('state')
    city = request.args.get('city')
    
    query = Cartorio.query
    if state:
        query = query.filter_by(state=state)
    if city:
        query = query.filter_by(city=city)
    
    cartorios = query.all()
    return jsonify([cartorio.to_dict() for cartorio in cartorios])

@cartorio_bp.route('/api/cartorios', methods=['POST'])
def create_cartorio():
    data = request.json
    cartorio = Cartorio(
        name=data['name'],
        city=data.get('city'),
        state=data.get('state'),
        phone=data.get('phone'),
        email=data.get('email'),
        whatsapp=data.get('whatsapp')
    )
    db.session.add(cartorio)
    db.session.commit()
    return jsonify(cartorio.to_dict()), 201

@cartorio_bp.route('/api/cartorios/<int:cartorio_id>', methods=['PUT'])
def update_cartorio(cartorio_id):
    cartorio = Cartorio.query.get_or_404(cartorio_id)
    data = request.json
    
    for key in ['name', 'city', 'state', 'phone', 'email', 'whatsapp']:
        if key in data:
            setattr(cartorio, key, data[key])
    
    db.session.commit()
    return jsonify(cartorio.to_dict())

@cartorio_bp.route('/api/cartorios/<int:cartorio_id>', methods=['DELETE'])
def delete_cartorio(cartorio_id):
    cartorio = Cartorio.query.get_or_404(cartorio_id)
    db.session.delete(cartorio)
    db.session.commit()
    return '', 204
