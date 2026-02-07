from sqlalchemy.orm import Session

from app.models.profissional import Profissional
from app.schemas.profissional import ProfissionalCreate, ProfissionalUpdate


# =========================================================
# CREATE
# =========================================================
def create_profissional(
    db: Session,
    data: ProfissionalCreate,
) -> Profissional:
    # Evita duplicidade por CPF
    existente = (
        db.query(Profissional)
        .filter(Profissional.cpf == data.cpf)
        .first()
    )
    if existente:
        raise ValueError("Já existe um profissional cadastrado com este CPF.")

    profissional = Profissional(
        nome_completo=data.nome_completo,
        cpf=data.cpf,
        email=data.email,
        telefone=data.telefone,
        conselho=data.conselho,
        numero_registro=data.numero_registro,
        uf_registro=data.uf_registro,
        especialidades=data.especialidades,
        ativo=data.ativo,
        avaliacao_media=data.avaliacao_media,
        total_projetos=data.total_projetos,
        observacoes=data.observacoes,
    )

    db.add(profissional)
    db.commit()
    db.refresh(profissional)
    return profissional


# =========================================================
# LIST
# =========================================================
def list_profissionais(db: Session) -> list[Profissional]:
    return (
        db.query(Profissional)
        .order_by(Profissional.nome_completo.asc())
        .all()
    )


# =========================================================
# GET
# =========================================================
def get_profissional(
    db: Session,
    profissional_id: int,
) -> Profissional | None:
    return (
        db.query(Profissional)
        .filter(Profissional.id == profissional_id)
        .first()
    )


# =========================================================
# UPDATE
# =========================================================
def update_profissional(
    db: Session,
    profissional_id: int,
    data: ProfissionalUpdate,
) -> Profissional | None:
    profissional = get_profissional(db, profissional_id)
    if not profissional:
        return None

    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(profissional, field, value)

    db.commit()
    db.refresh(profissional)
    return profissional


# =========================================================
# DELETE (SOFT LOGIC READY)
# =========================================================
def delete_profissional(
    db: Session,
    profissional_id: int,
) -> bool:
    profissional = get_profissional(db, profissional_id)
    if not profissional:
        return False

    # 🔒 Não removemos fisicamente — apenas desativamos
    profissional.ativo = False
    db.commit()
    return True
