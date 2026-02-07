# app/core/deps.py
from fastapi import Depends, HTTPException, status, Header
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User

ALGORITHM = settings.ALGORITHM


def _decode_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    return user


# =========================================================
# AUTENTICAÇÃO OBRIGATÓRIA (Bearer <token>)
# =========================================================
def get_current_user_required(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header inválido",
        )

    token = authorization.replace("Bearer ", "").strip()
    return _decode_token(token, db)


# =========================================================
# AUTENTICAÇÃO OPCIONAL
# =========================================================
def get_current_user_optional(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "").strip()
    try:
        return _decode_token(token, db)
    except HTTPException:
        return None


# 🔒 ALIAS DE COMPATIBILIDADE
get_current_user = get_current_user_required
