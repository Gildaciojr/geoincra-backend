from sqlalchemy.orm import Session

from app.models.confrontante import Confrontante
from app.models.imovel import Imovel
from app.schemas.confrontante import ConfrontanteCreate, ConfrontanteUpdate


def create_confrontante(db: Session, imovel_id: int, data: ConfrontanteCreate) -> Confrontante:
    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado.")

    new_item = Confrontante(
        imovel_id=imovel_id,
        direcao=data.direcao,
        nome_confrontante=data.nome_confrontante,
        matricula_confrontante=data.matricula_confrontante,
        descricao=data.descricao,
        identificacao_imovel_confrontante=data.identificacao_imovel_confrontante,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


def list_confrontantes(db: Session, imovel_id: int) -> list[Confrontante]:
    return (
        db.query(Confrontante)
        .filter(Confrontante.imovel_id == imovel_id)
        .order_by(Confrontante.id.asc())
        .all()
    )


def get_confrontante(db: Session, confrontante_id: int) -> Confrontante | None:
    return db.query(Confrontante).filter(Confrontante.id == confrontante_id).first()


def update_confrontante(db: Session, confrontante_id: int, data: ConfrontanteUpdate) -> Confrontante | None:
    item = get_confrontante(db, confrontante_id)
    if not item:
        return None

    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


def delete_confrontante(db: Session, confrontante_id: int) -> bool:
    item = get_confrontante(db, confrontante_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
