from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.project import Project

project_bp = Blueprint('project', __name__)

@project_bp.route('/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    return jsonify([project.to_dict() for project in projects])

@project_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict())

@project_bp.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    
    new_project = Project(
        name=data.get('name'),
        description=data.get('description'),
        status=data.get('status', 'Em Andamento'),
        area_hectares=data.get('area_hectares'),
        owner_name=data.get('owner_name'),
        owner_cpf=data.get('owner_cpf'),
        property_ccir=data.get('property_ccir'),
        property_matricula=data.get('property_matricula'),
        user_id=data.get('user_id')
    )
    
    db.session.add(new_project)
    db.session.commit()
    
    return jsonify(new_project.to_dict()), 201

@project_bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    project.area_hectares = data.get('area_hectares', project.area_hectares)
    project.owner_name = data.get('owner_name', project.owner_name)
    project.owner_cpf = data.get('owner_cpf', project.owner_cpf)
    project.property_ccir = data.get('property_ccir', project.property_ccir)
    project.property_matricula = data.get('property_matricula', project.property_matricula)
    
    db.session.commit()
    
    return jsonify(project.to_dict())

@project_bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    
    return jsonify({'message': 'Project deleted successfully'}), 200
