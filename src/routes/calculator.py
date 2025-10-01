from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.calculation_parameter import CalculationParameter

calculator_bp = Blueprint('calculator', __name__)

@calculator_bp.route('/calculate', methods=['POST'])
def calculate_budget():
    data = request.get_json()
    area = data.get('area_hectares')
    
    if not area:
        return jsonify({'error': 'Area is required'}), 400
    
    # Buscar o parâmetro de cálculo apropriado
    parameter = CalculationParameter.query.filter(
        CalculationParameter.min_area <= area,
        CalculationParameter.max_area >= area
    ).first()
    
    if not parameter:
        # Se não encontrar, usar o último parâmetro (maior área)
        parameter = CalculationParameter.query.order_by(CalculationParameter.max_area.desc()).first()
    
    if not parameter:
        return jsonify({'error': 'No calculation parameters found'}), 404
    
    # Calcular o valor
    calculated_value = area * parameter.price_per_hectare
    final_value = max(calculated_value, parameter.minimum_price)
    
    return jsonify({
        'area_hectares': area,
        'price_per_hectare': parameter.price_per_hectare,
        'calculated_value': calculated_value,
        'minimum_price': parameter.minimum_price,
        'final_value': final_value,
        'parameter_used': parameter.to_dict()
    })

@calculator_bp.route('/calculation-parameters', methods=['GET'])
def get_calculation_parameters():
    parameters = CalculationParameter.query.all()
    return jsonify([param.to_dict() for param in parameters])

@calculator_bp.route('/calculation-parameters', methods=['POST'])
def create_calculation_parameter():
    data = request.get_json()
    
    new_parameter = CalculationParameter(
        min_area=data.get('min_area'),
        max_area=data.get('max_area'),
        price_per_hectare=data.get('price_per_hectare'),
        minimum_price=data.get('minimum_price'),
        description=data.get('description')
    )
    
    db.session.add(new_parameter)
    db.session.commit()
    
    return jsonify(new_parameter.to_dict()), 201
