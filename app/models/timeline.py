from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class TimelineEntry(Base):
    __tablename__ = "timeline_entries"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)

    status = Column(String(50), nullable=True)
    etapa = Column(String(100), nullable=True)  # análise, campo, sigef, cartório

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="timeline_entries", lazy="joined")
