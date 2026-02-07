from sqlalchemy.orm import Session
from app.models.municipio import Municipio


class MunicipioService:

    @staticmethod
    def listar_todos(db: Session):
        return db.query(Municipio).order_by(Municipio.nome.asc()).all()

    @staticmethod
    def buscar(db: Session, nome: str, uf: str = "RO"):
        return (
            db.query(Municipio)
            .filter(Municipio.nome.ilike(nome))
            .filter(Municipio.estado == uf)
            .first()
        )

    @staticmethod
    def faixas(db: Session, nome: str, uf: str = "RO"):
        municipio = MunicipioService.buscar(db, nome, uf)
        if not municipio:
            return None

        return {
            "municipio": municipio.nome,
            "estado": municipio.estado,
            "vti_min": municipio.vti_min,
            "vtn_min": municipio.vtn_min,
        }
