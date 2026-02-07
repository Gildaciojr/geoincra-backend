from sqlalchemy.orm import Session
from app.models.proprietario import Proprietario
from app.models.imovel import Imovel
from app.schemas.proprietario import (
    ProprietarioCreate,
    ProprietarioUpdate,
)


# =========================================================
# CREATE
# =========================================================

def create_proprietario(
    db: Session,
    imovel_id: int,
    data: ProprietarioCreate,
) -> Proprietario:
    # 🔒 Valida se o imóvel existe
    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado.")

    proprietario = Proprietario(
        imovel_id=imovel_id,
        nome_completo=data.nome_completo,
        tipo_pessoa=data.tipo_pessoa,

        cpf=data.cpf,
        cnpj=data.cnpj,

        rg=data.rg,
        orgao_emissor=data.orgao_emissor,

        estado_civil=data.estado_civil,
        profissao=data.profissao,
        nacionalidade=data.nacionalidade,

        endereco=data.endereco,
        municipio=data.municipio,
        estado=data.estado,
        cep=data.cep,

        telefone=data.telefone,
        email=data.email,

        observacoes=data.observacoes,
    )

    db.add(proprietario)
    db.commit()
    db.refresh(proprietario)
    return proprietario


# =========================================================
# LIST
# =========================================================

def list_proprietarios_by_imovel(
    db: Session,
    imovel_id: int,
) -> list[Proprietario]:
    return (
        db.query(Proprietario)
        .filter(Proprietario.imovel_id == imovel_id)
        .order_by(Proprietario.created_at.asc())
        .all()
    )


# =========================================================
# GET
# =========================================================

def get_proprietario(
    db: Session,
    proprietario_id: int,
) -> Proprietario | None:
    return (
        db.query(Proprietario)
        .filter(Proprietario.id == proprietario_id)
        .first()
    )


# =========================================================
# UPDATE
# =========================================================

def update_proprietario(
    db: Session,
    proprietario_id: int,
    data: ProprietarioUpdate,
) -> Proprietario | None:
    proprietario = get_proprietario(db, proprietario_id)
    if not proprietario:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(proprietario, field, value)

    db.commit()
    db.refresh(proprietario)
    return proprietario


# =========================================================
# DELETE
# =========================================================

def delete_proprietario(
    db: Session,
    proprietario_id: int,
) -> bool:
    proprietario = get_proprietario(db, proprietario_id)
    if not proprietario:
        return False

    db.delete(proprietario)
    db.commit()
    return True
