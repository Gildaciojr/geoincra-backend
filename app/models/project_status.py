from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProjectStatus(Base):
    __tablename__ = "project_status"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "status",
            name="uq_project_status_atual",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # 🔗 RELAÇÃO COM PROJETO
    # =========================================================
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # STATUS / ETAPA
    # =========================================================
    # EXEMPLOS:
    # CADASTRADO
    # DOCUMENTOS_EM_ANALISE
    # AJUSTES_SOLICITADOS
    # APROVADO_TECNICAMENTE
    # PRONTO_PARA_SIGEF
    # ENVIADO_SIGEF
    # FINALIZADO
    status = Column(String(60), nullable=False)

    descricao = Column(Text, nullable=True)

    # =========================================================
    # CONTROLE
    # =========================================================
    ativo = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    definido_automaticamente = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    definido_por_usuario_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    definido_em = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    project = relationship(
        "Project",
        backref="status_historico",
        lazy="joined",
    )

    usuario = relationship(
        "User",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectStatus project_id={self.project_id} "
            f"status={self.status} ativo={self.ativo}>"
        )
