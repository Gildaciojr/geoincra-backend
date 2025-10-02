from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.document import Document
import os
from werkzeug.utils import secure_filename

document_bp = Blueprint('document', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@document_bp.route('/api/documents', methods=['GET'])
def get_documents():
    project_id = request.args.get('project_id')
    if project_id:
        documents = Document.query.filter_by(project_id=project_id).all()
    else:
        documents = Document.query.all()
    return jsonify([doc.to_dict() for doc in documents])

@document_bp.route('/api/documents', methods=['POST'])
def create_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        document = Document(
            project_id=request.form.get('project_id'),
            document_type=request.form.get('document_type', 'Outros'),
            file_name=filename,
            file_path=filepath,
            status='Pendente'
        )
        db.session.add(document)
        db.session.commit()
        
        return jsonify(document.to_dict()), 201
    
    return jsonify({'error': 'File type not allowed'}), 400

@document_bp.route('/api/documents/<int:document_id>', methods=['PUT'])
def update_document(document_id):
    document = Document.query.get_or_404(document_id)
    data = request.json
    
    if 'status' in data:
        document.status = data['status']
    if 'extracted_data' in data:
        document.extracted_data = data['extracted_data']
    
    db.session.commit()
    return jsonify(document.to_dict())

@document_bp.route('/api/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    db.session.delete(document)
    db.session.commit()
    return '', 204
