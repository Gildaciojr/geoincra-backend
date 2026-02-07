from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.calculation_parameter import (
    CalculationParameterCreate,
    CalculationParameterUpdate,
    CalculationParameterRead,
)
from app.crud.calculation_parameter_crud import (
    get_all_parameters,
    get_parameter,
    create_parameter,
    update_parameter,
    delete_parameter,
)

router = APIRouter()


@router.get("/calculation-parameters", response_model=list[CalculationParameterRead])
def list_parameters(db: Session = Depends(get_db)):
    return get_all_parameters(db)


@router.get(
    "/calculation-parameters/{parameter_id}",
    response_model=CalculationParameterRead,
)
def read_parameter(parameter_id: int, db: Session = Depends(get_db)):
    param = get_parameter(db, parameter_id)
    if not param:
        raise HTTPException(404, "Parâmetro não encontrado")
    return param


@router.post("/calculation-parameters", response_model=CalculationParameterRead)
def create_new_parameter(
    data: CalculationParameterCreate,
    db: Session = Depends(get_db),
):
    return create_parameter(db, data)


@router.put(
    "/calculation-parameters/{parameter_id}",
    response_model=CalculationParameterRead,
)
def update_existing_parameter(
    parameter_id: int,
    data: CalculationParameterUpdate,
    db: Session = Depends(get_db),
):
    param = update_parameter(db, parameter_id, data)
    if not param:
        raise HTTPException(404, "Parâmetro não encontrado")
    return param


@router.delete("/calculation-parameters/{parameter_id}")
def delete_existing_parameter(
    parameter_id: int,
    db: Session = Depends(get_db),
):
    success = delete_parameter(db, parameter_id)
    if not success:
        raise HTTPException(404, "Parâmetro não encontrado")
    return {"status": "deleted"}
