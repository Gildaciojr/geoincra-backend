# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# -------------------------------------------------------------
# CONFIGURAÇÃO DO BANCO
# -------------------------------------------------------------
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,   # evita erro de conexão perdida
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# -------------------------------------------------------------
# FUNÇÃO get_db (necessária para FastAPI)
# -------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
