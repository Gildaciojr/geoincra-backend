# app/models/__init__.py
# Importar TODOS os models aqui garante que o SQLAlchemy registre as tabelas
# quando você chamar Base.metadata.create_all() no init_db.

from app.core.database import Base

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
from app.models.proposta_profissional import PropostaProfissional
from app.models.proprietario import Proprietario
from app.models.sobreposicao import Sobreposicao
from app.models.timeline import TimelineEntry
from app.models.proposal import Proposal
from app.models.user import User

__all__ = [
    "Base",
    "AuditLog",
    "AvaliacaoProfissional",
    "CalculationParameter",
    "Cartorio",
    "Confrontante",
    "Document",
    "DocumentoTecnicoChecklist",
    "DocumentoTecnico",
    "Geometria",
    "Imovel",
    "Matricula",
    "Municipio",
    "PagamentoEvento",
    "Pagamento",
    "ParcelaPagamento",
    "ProfissionalRanking",
    "ProfissionalSelecao",
    "Profissional",
    "ProjectMarco",
    "ProjectStatus",
    "Project",
    "ProjetoProfissional",
    "PropostaProfissional",
    "Proprietario",
    "Sobreposicao",
    "TimelineEntry",
    "Proposal",
    "User",
]
