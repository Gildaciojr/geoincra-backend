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
    tipo_pessoa = data.tipo_pessoa.upper()

    if tipo_pessoa == "FISICA":
        existente = (
            db.query(Profissional)
            .filter(Profissional.cpf == data.cpf)
            .first()
        )
        if existente:
            raise ValueError("Já existe um profissional cadastrado com este CPF.")
    else:
        existente = (
            db.query(Profissional)
            .filter(Profissional.cnpj == data.cnpj)
            .first()
        )
        if existente:
            raise ValueError("Já existe um profissional cadastrado com este CNPJ.")

    profissional = Profissional(
        nome_completo=data.nome_completo,
        tipo_pessoa=tipo_pessoa,
        cpf=data.cpf if tipo_pessoa == "FISICA" else None,
        cnpj=data.cnpj if tipo_pessoa == "JURIDICA" else None,
        email=data.email,
        telefone=data.telefone,
        crea=data.numero_registro,
        uf_crea=data.uf_registro,
        especialidades=data.especialidades,
        ativo=data.ativo,
        rating_medio=float(data.avaliacao_media or 0),
        total_servicos=int(data.total_projetos or 0),
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

    # 🔥 MAPEAMENTO CORRETO
    if "avaliacao_media" in payload:
        profissional.rating_medio = float(payload.pop("avaliacao_media"))

    if "total_projetos" in payload:
        profissional.total_servicos = int(payload.pop("total_projetos"))

    for field, value in payload.items():
        setattr(profissional, field, value)

    db.commit()
    db.refresh(profissional)
    return profissional


# =========================================================
# DELETE
# =========================================================
def delete_profissional(
    db: Session,
    profissional_id: int,
) -> bool:
    profissional = get_profissional(db, profissional_id)
    if not profissional:
        return False

    profissional.ativo = False
    db.commit()
    return True