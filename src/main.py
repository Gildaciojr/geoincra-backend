import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.project import project_bp
from src.routes.calculator import calculator_bp
from src.routes.confrontante import confrontante_bp
from src.routes.document import document_bp
from src.routes.cartorio import cartorio_bp
from src.routes.timeline import timeline_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Enable CORS for all routes
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(project_bp, url_prefix='/api')
app.register_blueprint(calculator_bp, url_prefix='/api')
app.register_blueprint(confrontante_bp, url_prefix='/api')
app.register_blueprint(document_bp)
app.register_blueprint(cartorio_bp)
app.register_blueprint(timeline_bp)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Import models to ensure they're registered with SQLAlchemy
from src.models.project import Project
from src.models.confrontante import Confrontante
from src.models.calculation_parameter import CalculationParameter
from src.models.document import Document
from src.models.cartorio import Cartorio
from src.models.timeline import Timeline

with app.app_context():
    db.create_all()
    
    # Seed calculation parameters if table is empty
    if CalculationParameter.query.count() == 0:
        params = [
            CalculationParameter(min_area=0, max_area=50, price_per_hectare=120.0, minimum_price=3000.0, description='0 - 50 hectares'),
            CalculationParameter(min_area=51, max_area=200, price_per_hectare=95.0, minimum_price=6000.0, description='51 - 200 hectares'),
            CalculationParameter(min_area=201, max_area=999999, price_per_hectare=75.0, minimum_price=15000.0, description='201+ hectares')
        ]
        for param in params:
            db.session.add(param)
        db.session.commit()
        print("Calculation parameters seeded successfully")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
