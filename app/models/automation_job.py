from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)

from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)

from sqlalchemy.sql import func

from sqlalchemy.types import Enum as SAEnum

from app.core.database import Base


# =========================================================
# ENUMS EXISTENTES (NÃO ALTERAR)
# =========================================================

AutomationTypeEnum = SAEnum(
    "RI_DIGITAL_MATRICULA",
    "ONR_SIGRI_CONSULTA",
    "RI_DIGITAL_SOLICITAR_CERTIDAO",
    "RI_DIGITAL_CONSULTAR_CERTIDAO",
    "OCR_DOCUMENT",
    name="automation_type",
    native_enum=True,
    create_type=False,
)

AutomationStatusEnum = SAEnum(
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="automation_status",
    native_enum=True,
    create_type=False,
)


class AutomationJob(Base):
    __tablename__ = "automation_jobs"

    # =====================================================
    # IDENTIDADE
    # =====================================================

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # =====================================================
    # RELAÇÕES
    # =====================================================

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    project_id = Column(
        Integer,
        ForeignKey(
            "projects.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # =====================================================
    # JOB
    # =====================================================

    type = Column(
        AutomationTypeEnum,
        nullable=False,
    )

    status = Column(
        AutomationStatusEnum,
        nullable=False,
        server_default=text(
            "'PENDING'::automation_status"
        ),
    )

    # =====================================================
    # PIPELINE
    # =====================================================

    pipeline_tipo = Column(
        String(100),
        nullable=True,
        index=True,
    )

    pipeline_stage = Column(
        String(100),
        nullable=True,
    )

    parser_utilizado = Column(
        String(255),
        nullable=True,
    )

    normalizador_utilizado = Column(
        String(255),
        nullable=True,
    )

    engine_version = Column(
        String(100),
        nullable=True,
    )

    parser_version = Column(
        String(100),
        nullable=True,
    )

    normalizer_version = Column(
        String(100),
        nullable=True,
    )

    schema_version = Column(
        String(100),
        nullable=True,
    )

    # =====================================================
    # PRIORIDADE / FILA
    # =====================================================

    prioridade = Column(
        String(20),
        nullable=False,
        server_default=text("'NORMAL'"),
    )

    queue_name = Column(
        String(100),
        nullable=True,
    )

    worker_hostname = Column(
        String(255),
        nullable=True,
    )

    worker_pid = Column(
        Integer,
        nullable=True,
    )

    # =====================================================
    # PAYLOAD
    # =====================================================

    payload_json = Column(
        JSONB,
        nullable=False,
    )

    resultado_json = Column(
        JSONB,
        nullable=True,
    )

    metadata_json = Column(
        JSONB,
        nullable=True,
    )

    # =====================================================
    # RETRY / RESILIÊNCIA
    # =====================================================

    retry_count = Column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    retry_limit = Column(
        Integer,
        nullable=False,
        server_default=text("3"),
    )

    pode_reprocessar = Column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    reprocessado = Column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    # =====================================================
    # ERROS
    # =====================================================

    error_message = Column(
        Text,
        nullable=True,
    )

    error_traceback = Column(
        Text,
        nullable=True,
    )

    ultimo_erro_em = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # EXECUÇÃO
    # =====================================================

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    heartbeat_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    timeout_seconds = Column(
        Integer,
        nullable=True,
    )

    # =====================================================
    # AUDITORIA
    # =====================================================

    observacoes = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )