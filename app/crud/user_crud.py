# app/crud/user_crud.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate):
    hashed_pw = get_password_hash(user.password)

    db_user = User(
        full_name=user.full_name,
        email=user.email,
        password_hash=hashed_pw,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def list_users(db: Session):
    return db.query(User).all()
