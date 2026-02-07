from datetime import datetime
from sqlalchemy.orm import Session

from app.models.proposta_profissional import PropostaProfissional
from app.models.project import Project
from app.models.profissional import Profissional
from app.schemas.proposta_profissional import (
    PropostaProfissionalCreate,
    PropostaProfissionalResposta,
)


# =========================================================
# ENVIAR PROPOSTA
# =========================================================
def enviar_proposta(
    db: Session,
    project_id: int,
    data: PropostaProfissionalCreate,
) -> PropostaProfissional:
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError("Projeto não encontrado.")

    profissional = db.query(Profissional).get(data.profissional_id)
    if not profissional or not profissional.ativo:
        raise ValueError("Profissional inválido ou inativo.")

    existente = (
        db.query(PropostaProfissional)
        .filter(
            PropostaProfissional.project_id == project_id,
            PropostaProfissional.profissional_id == data.profissional_id,
        )
        .first()
    )
    if existente:
        raise ValueError("Já existe proposta enviada para este profissional.")

    proposta = PropostaProfissional(
        project_id=project_id,
        profissional_id=data.profissional_id,
        valor_proposto=data.valor_proposto,
        prazo_dias=data.prazo_dias,
        observacoes=data.observacoes,
    )

    db.add(proposta)
    db.commit()
    db.refresh(proposta)
    return proposta


# =========================================================
# RESPONDER PROPOSTA
# =========================================================
def responder_proposta(
    db: Session,
    proposta_id: int,
    data: PropostaProfissionalResposta,
) -> PropostaProfissional | None:
    proposta = (
        db.query(PropostaProfissional)
        .filter(PropostaProfissional.id == proposta_id)
        .first()
    )
    if not proposta:
        return None

    if proposta.status != "ENVIADA":
        raise ValueError("Esta proposta já foi respondida.")

    proposta.status = "ACEITA" if data.aceitar else "RECUSADA"
    proposta.respondida_em = datetime.utcnow()

    if data.observacoes:
        proposta.observacoes = data.observacoes

    # 🔥 Regra futura:
    # Se ACEITA → vincular profissional ao projeto (fase seguinte)

    db.commit()
    db.refresh(proposta)
    return proposta


# =========================================================
# LISTAR PROPOSTAS POR PROJETO
# =========================================================
def listar_propostas_por_projeto(
    db: Session,
    project_id: int,
) -> list[PropostaProfissional]:
    return (
        db.query(PropostaProfissional)
        .filter(PropostaProfissional.project_id == project_id)
        .order_by(PropostaProfissional.enviada_em.desc())
        .all()
    )
