from sqlalchemy.orm import Session
from app.models.calculation_parameter import CalculationParameter
from app.schemas.calculation_parameter import (
    CalculationParameterCreate,
    CalculationParameterUpdate,
)


def get_all_parameters(db: Session):
    return db.query(CalculationParameter).order_by(CalculationParameter.nome.asc()).all()


def get_parameter(db: Session, parameter_id: int):
    return (
        db.query(CalculationParameter)
        .filter(CalculationParameter.id == parameter_id)
        .first()
    )


def create_parameter(db: Session, data: CalculationParameterCreate):
    param = CalculationParameter(**data.model_dump())
    db.add(param)
    db.commit()
    db.refresh(param)
    return param


def update_parameter(
    db: Session,
    parameter_id: int,
    data: CalculationParameterUpdate,
):
    param = get_parameter(db, parameter_id)
    if not param:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(param, field, value)

    db.commit()
    db.refresh(param)
    return param


def delete_parameter(db: Session, parameter_id: int):
    param = get_parameter(db, parameter_id)
    if not param:
        return False

    db.delete(param)
    db.commit()
    return True
