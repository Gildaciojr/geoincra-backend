from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Opcional: documento pode estar vinculado a uma matrícula (quando fizer sentido)
    matricula_id = Column(
        Integer,
        ForeignKey("matriculas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    doc_type = Column(String(50), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Caminho absoluto/relativo no servidor (necessário p/ servir/baixar corretamente)
    file_path = Column(String(512), nullable=True)

    uploaded_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    observacoes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="documents", lazy="joined")

    matricula = relationship("Matricula", back_populates="documentos", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} "
            f"type={self.doc_type} "
            f"project_id={self.project_id}>"
        )
