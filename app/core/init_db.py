from __future__ import annotations

# =========================================================
# DATABASE / BASE
# =========================================================
from app.core.database import Base, engine

# =========================================================
# IMPORTAÇÃO DE TODOS OS MODELS
# (OBRIGATÓRIO para o SQLAlchemy registrar no metadata)
# =========================================================

from app.models.audit_log import AuditLog
from app.models.avaliacao_profissional import AvaliacaoProfissional
from app.models.calculation_parameter import CalculationParameter
from app.models.cartorio import Cartorio
from app.models.confrontante import Confrontante
from app.models.document import Document
from app.models.documento_tecnico_checklist import DocumentoTecnicoChecklist
from app.models.documento_tecnico import DocumentoTecnico
from app.models.geometria import Geometria
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.models.municipio import Municipio
from app.models.pagamento_evento import PagamentoEvento
from app.models.pagamento import Pagamento
from app.models.parcela_pagamento import ParcelaPagamento
from app.models.profissional_ranking import ProfissionalRanking
from app.models.profissional_selecao import ProfissionalSelecao
from app.models.profissional import Profissional
from app.models.project_marco import ProjectMarco
from app.models.project_status import ProjectStatus
from app.models.project import Project
from app.models.projeto_profissional import ProjetoProfissional
from app.models.proposal import Proposal
from app.models.proposta_profissional import PropostaProfissional
from app.models.proprietario import Proprietario
from app.models.sobreposicao import Sobreposicao
from app.models.timeline import TimelineEntry
from app.models.user import User

# =========================================================
# FUNÇÃO DE INICIALIZAÇÃO DO BANCO (DEV)
# =========================================================

def init_db() -> None:
    """
    Cria todas as tabelas do banco de dados com base nos models.
    ⚠️ USAR APENAS EM DESENVOLVIMENTO.
    Em produção, utilizar Alembic (migrations).
    """
    Base.metadata.create_all(bind=engine)


# =========================================================
# EXECUÇÃO DIRETA VIA CLI
# =========================================================

if __name__ == "__main__":
    init_db()
    print("✅ Banco de dados inicializado com sucesso.")
