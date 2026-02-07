# app/routes/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import create_access_token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.crud.user_crud import create_user, authenticate_user, get_user_by_email

router = APIRouter(tags=["Auth"])


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    db_user = create_user(db, user)

    token = create_access_token(subject=str(db_user.id))



    return {
        "access_token": token,
        "user": UserResponse.from_orm(db_user),
    }


@router.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )

    token = create_access_token(subject=str(user.id))

    return {
        "access_token": token,
        "user": UserResponse.from_orm(user),
    }
