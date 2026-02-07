from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.schemas.matricula import MatriculaCreate, MatriculaUpdate


# =========================================================
# CREATE
# =========================================================
def create_matricula(
    db: Session,
    imovel_id: int,
    data: MatriculaCreate,
) -> Matricula:
    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado.")

    obj = Matricula(
        imovel_id=imovel_id,
        cartorio_id=data.cartorio_id,
        numero_matricula=data.numero_matricula,
        livro=data.livro,
        folha=data.folha,
        comarca=data.comarca,
        codigo_cartorio=data.codigo_cartorio,
        data_abertura=data.data_abertura,
        data_ultima_atualizacao=data.data_ultima_atualizacao,
        inteiro_teor=data.inteiro_teor,
        arquivo_path=data.arquivo_path,
        status=(data.status or "ATIVA").upper().strip(),
        observacoes=data.observacoes,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# =========================================================
# LIST
# =========================================================
def list_matriculas_by_imovel(db: Session, imovel_id: int) -> list[Matricula]:
    return (
        db.query(Matricula)
        .filter(Matricula.imovel_id == imovel_id)
        .order_by(Matricula.id.desc())
        .all()
    )


# =========================================================
# GET
# =========================================================
def get_matricula(db: Session, matricula_id: int) -> Matricula | None:
    return db.query(Matricula).filter(Matricula.id == matricula_id).first()


# =========================================================
# UPDATE
# =========================================================
def update_matricula(
    db: Session,
    matricula_id: int,
    data: MatriculaUpdate,
) -> Matricula | None:
    obj = get_matricula(db, matricula_id)
    if not obj:
        return None

    payload = data.model_dump(exclude_unset=True)

    if "status" in payload and payload["status"] is not None:
        payload["status"] = str(payload["status"]).upper().strip()

    for field, value in payload.items():
        setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


# =========================================================
# DELETE
# =========================================================
def delete_matricula(db: Session, matricula_id: int) -> bool:
    obj = get_matricula(db, matricula_id)
    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True
