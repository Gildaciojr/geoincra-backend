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


class DocumentoTecnicoChecklist(Base):
    __tablename__ = "documentos_tecnicos_checklist"

    __table_args__ = (
        UniqueConstraint(
            "documento_tecnico_id",
            "chave",
            name="uq_doc_tecnico_checklist_item",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # 🔗 RELAÇÃO COM DOCUMENTO TÉCNICO (VERSÃO ESPECÍFICA)
    # =========================================================
    documento_tecnico_id = Column(
        Integer,
        ForeignKey("documentos_tecnicos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # DEFINIÇÃO DO ITEM DE CHECKLIST
    # =========================================================
    chave = Column(
        String(80),
        nullable=False,
        comment="Identificador técnico do item (ex: AREA_CONFERE, VERTICES_FECHADOS)",
    )

    descricao = Column(
        String(255),
        nullable=False,
        comment="Descrição humana do item de validação",
    )

    obrigatorio = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # =========================================================
    # RESULTADO DA VALIDAÇÃO
    # =========================================================
    # OK | ALERTA | ERRO | NA
    status = Column(
        String(20),
        nullable=False,
        default="NA",
    )

    mensagem = Column(
        Text,
        nullable=True,
        comment="Mensagem técnica explicativa (erro, alerta, observação)",
    )

    validado_automaticamente = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    validado_por_usuario_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    validado_em = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    documento_tecnico = relationship(
        "DocumentoTecnico",
        backref="checklist_itens",
        lazy="joined",
    )

    usuario_validador = relationship(
        "User",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentoTecnicoChecklist id={self.id} "
            f"doc_id={self.documento_tecnico_id} "
            f"chave={self.chave} "
            f"status={self.status}>"
        )
