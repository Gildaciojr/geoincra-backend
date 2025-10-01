from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.confrontante import Confrontante

confrontante_bp = Blueprint('confrontante', __name__)

@confrontante_bp.route('/confrontantes', methods=['GET'])
def get_confrontantes():
    project_id = request.args.get('project_id')
    if project_id:
        confrontantes = Confrontante.query.filter_by(project_id=project_id).all()
    else:
        confrontantes = Confrontante.query.all()
    return jsonify([confrontante.to_dict() for confrontante in confrontantes])

@confrontante_bp.route('/confrontantes/<int:confrontante_id>', methods=['GET'])
def get_confrontante(confrontante_id):
    confrontante = Confrontante.query.get_or_404(confrontante_id)
    return jsonify(confrontante.to_dict())

@confrontante_bp.route('/confrontantes', methods=['POST'])
def create_confrontante():
    data = request.get_json()
    
    new_confrontante = Confrontante(
        project_id=data.get('project_id'),
        name=data.get('name'),
        cpf=data.get('cpf'),
        spouse_name=data.get('spouse_name'),
        spouse_cpf=data.get('spouse_cpf'),
        address=data.get('address'),
        property_name=data.get('property_name'),
        property_ccir=data.get('property_ccir'),
        property_matricula=data.get('property_matricula')
    )
    
    db.session.add(new_confrontante)
    db.session.commit()
    
    return jsonify(new_confrontante.to_dict()), 201

@confrontante_bp.route('/confrontantes/<int:confrontante_id>', methods=['PUT'])
def update_confrontante(confrontante_id):
    confrontante = Confrontante.query.get_or_404(confrontante_id)
    data = request.get_json()
    
    confrontante.name = data.get('name', confrontante.name)
    confrontante.cpf = data.get('cpf', confrontante.cpf)
    confrontante.spouse_name = data.get('spouse_name', confrontante.spouse_name)
    confrontante.spouse_cpf = data.get('spouse_cpf', confrontante.spouse_cpf)
    confrontante.address = data.get('address', confrontante.address)
    confrontante.property_name = data.get('property_name', confrontante.property_name)
    confrontante.property_ccir = data.get('property_ccir', confrontante.property_ccir)
    confrontante.property_matricula = data.get('property_matricula', confrontante.property_matricula)
    
    db.session.commit()
    
    return jsonify(confrontante.to_dict())

@confrontante_bp.route('/confrontantes/<int:confrontante_id>', methods=['DELETE'])
def delete_confrontante(confrontante_id):
    confrontante = Confrontante.query.get_or_404(confrontante_id)
    db.session.delete(confrontante)
    db.session.commit()
    
    return jsonify({'message': 'Confrontante deleted successfully'}), 200
