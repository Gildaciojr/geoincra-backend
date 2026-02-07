# app/routes/user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.user import UserCreate, UserResponse
from app.crud.user_crud import create_user, get_user_by_email, list_users

router = APIRouter()


@router.post("/", response_model=UserResponse)
def create_user_route(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    return create_user(db, user)


@router.get("/", response_model=list[UserResponse])
def list_users_route(db: Session = Depends(get_db)):
    return list_users(db)
