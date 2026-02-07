from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProjectMarco(Base):
    __tablename__ = "project_marcos"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "codigo",
            name="uq_project_marco_codigo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Ex.: CADASTRADO, DOCUMENTOS_OK, TECNICO_APROVADO, PRONTO_SIGEF
    codigo = Column(String(60), nullable=False)

    titulo = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=True)

    atingido = Column(Boolean, nullable=False, default=False)

    atingido_em = Column(DateTime(timezone=True), nullable=True)

    criado_automaticamente = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    project = relationship(
        "Project",
        backref="marcos",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectMarco project_id={self.project_id} "
            f"codigo={self.codigo} atingido={self.atingido}>"
        )
