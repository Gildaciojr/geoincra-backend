# geoincra_backend/app/routes/automacoes_routes.py
from __future__ import annotations

from uuid import UUID
from pathlib import Path
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.external_credential import ExternalCredential
from app.models.automation_job import AutomationJob
from app.models.automation_result import AutomationResult
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/automacoes")


# =========================================================
# Schemas (Pydantic) — PROFISSIONAL / PRODUÇÃO
# =========================================================
class RiDigitalCredenciaisPayload(BaseModel):
    login: str = Field(..., min_length=3)
    senha: str = Field(..., min_length=1)


class RiDigitalJobPayload(BaseModel):
    data_inicio: str = Field(..., description="YYYY-MM-DD")
    data_fim: str = Field(..., description="YYYY-MM-DD")
    project_id: Optional[int] = None
    usar_credencial_salva: bool = True
    login: Optional[str] = None
    senha: Optional[str] = None


class OnrConsultaPayload(BaseModel):
    project_id: int
    modo: str
    valor: str


def _serialize_job(job: AutomationJob, resultados: list[AutomationResult] | None = None) -> dict[str, Any]:
    """
    Serialização segura para o frontend (evita problemas com JSON/UUID/datetime).
    """
    return {
        "id": str(job.id),
        "user_id": job.user_id,
        "project_id": job.project_id,
        "type": job.type,
        "status": job.status,
        "payload_json": job.payload_json,
        "created_at": job.created_at.isoformat() if getattr(job, "created_at", None) else None,
        "started_at": job.started_at.isoformat() if getattr(job, "started_at", None) else None,
        "finished_at": job.finished_at.isoformat() if getattr(job, "finished_at", None) else None,
        "error_message": job.error_message,
        "resultados": [
            {
                "id": str(r.id),
                "job_id": str(r.job_id),
                "protocolo": r.protocolo,
                "matricula": r.matricula,
                "cnm": r.cnm,
                "cartorio": r.cartorio,
                "data_pedido": r.data_pedido.isoformat() if getattr(r, "data_pedido", None) else None,
                "file_path": r.file_path,
                "metadata_json": getattr(r, "metadata_json", None),
                "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
            }
            for r in (resultados or [])
        ],
    }


# =========================================================
# 🔐 CREDENCIAIS — RI DIGITAL (JSON BODY)
# =========================================================
@router.post("/credenciais/ri-digital")
def salvar_credenciais_ri_digital(
    payload: RiDigitalCredenciaisPayload = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = (
        db.query(ExternalCredential)
        .filter(
            ExternalCredential.user_id == user.id,
            ExternalCredential.provider == "RI_DIGITAL",
        )
        .first()
    )

    if cred:
        cred.login = payload.login
        cred.password_encrypted = payload.senha
        cred.active = True
    else:
        cred = ExternalCredential(
            user_id=user.id,
            provider="RI_DIGITAL",
            login=payload.login,
            password_encrypted=payload.senha,
            active=True,
        )
        db.add(cred)

    db.commit()

    return {
        "provider": "RI_DIGITAL",
        "login": payload.login[:3] + "***",
        "active": True,
    }


@router.get("/credenciais/ri-digital")
def obter_credenciais_ri_digital(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = (
        db.query(ExternalCredential)
        .filter(
            ExternalCredential.user_id == user.id,
            ExternalCredential.provider == "RI_DIGITAL",
            ExternalCredential.active.is_(True),
        )
        .first()
    )

    if not cred:
        return {"exists": False}

    return {
        "exists": True,
        "login": (cred.login[:3] + "***") if cred.login else "***",
        "active": cred.active,
    }


@router.delete("/credenciais/ri-digital")
def remover_credenciais_ri_digital(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = (
        db.query(ExternalCredential)
        .filter(
            ExternalCredential.user_id == user.id,
            ExternalCredential.provider == "RI_DIGITAL",
        )
        .first()
    )

    if cred:
        db.delete(cred)
        db.commit()

    return {"removed": True}


# =========================================================
# 🤖 JOB — RI DIGITAL (ACEITA JSON e TAMBÉM QUERY PARAMS)
# =========================================================
@router.post("/ri-digital/matriculas/jobs")
def criar_job_consulta_matriculas(
    # ✅ Compatibilidade: se vier JSON, usa payload. Se não vier, usa query params.
    payload: Optional[RiDigitalJobPayload] = Body(None),
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    project_id: Optional[int] = None,
    usar_credencial_salva: bool = True,
    login: Optional[str] = None,
    senha: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Normaliza entrada (JSON > query)
    if payload:
        data_inicio = payload.data_inicio
        data_fim = payload.data_fim
        project_id = payload.project_id
        usar_credencial_salva = payload.usar_credencial_salva
        login = payload.login
        senha = payload.senha

    if not data_inicio or not data_fim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="data_inicio e data_fim são obrigatórios",
        )

    if usar_credencial_salva:
        cred = (
            db.query(ExternalCredential)
            .filter(
                ExternalCredential.user_id == user.id,
                ExternalCredential.provider == "RI_DIGITAL",
                ExternalCredential.active.is_(True),
            )
            .first()
        )
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credenciais do RI Digital não encontradas",
            )
    else:
        if not login or not senha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login e senha são obrigatórios",
            )

    job = AutomationJob(
        user_id=user.id,
        project_id=project_id,
        type="RI_DIGITAL_MATRICULA",
        status="PENDING",
        payload_json={
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "usar_credencial_salva": usar_credencial_salva,
        },
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    if project_id:
        TimelineService.registrar_evento(
            db=db,
            project_id=project_id,
            titulo="Automação RI Digital — Matrículas",
            descricao=f"Consulta de matrículas de {data_inicio} até {data_fim}",
            status="Pendente",
        )

    return {"job_id": str(job.id), "status": job.status}


# =========================================================
# 🤖 JOB — ONR / SIG-RI (JSON BODY PROFISSIONAL)
# =========================================================
@router.post("/onr/consulta/jobs")
def criar_job_onr_consulta(
    payload: OnrConsultaPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == payload.project_id,
            Project.owner_id == user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado ou acesso negado",
        )

    modo_norm = (payload.modo or "").upper().strip()
    if modo_norm not in {"CAR", "ENDERECO", "LAT_LNG"}:
        raise HTTPException(
            status_code=400,
            detail="Modo inválido. Use CAR ou ENDERECO",
        )

    valor_norm = (payload.valor or "").strip()
    if len(valor_norm) < 3:
        raise HTTPException(
            status_code=400,
            detail="Valor inválido para consulta",
        )

    job = AutomationJob(
        user_id=user.id,
        project_id=payload.project_id,
        type="ONR_SIGRI_CONSULTA",
        status="PENDING",
        payload_json={
            "action": "CONSULTAR_IMOVEL",
            "search": {"type": modo_norm, "value": valor_norm},
        },
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    TimelineService.registrar_evento(
        db=db,
        project_id=payload.project_id,
        titulo="Automação ONR / SIG-RI",
        descricao=f"Consulta por {modo_norm}: {valor_norm}",
        status="Pendente",
    )

    return {"job_id": str(job.id), "status": job.status}


# =========================================================
# 📋 JOBS — LISTAGEM (JÁ VEM COM RESULTADOS)
# =========================================================
@router.get("/jobs")
def listar_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    type: str | None = Query(None),
):
    q = db.query(AutomationJob).filter(AutomationJob.user_id == user.id)
    if type:
        q = q.filter(AutomationJob.type == type)

    jobs = q.order_by(AutomationJob.created_at.desc()).all()

    # ✅ Embute resultados para o frontend (job.resultados existir)
    job_ids = [j.id for j in jobs]
    results_map: dict[UUID, list[AutomationResult]] = {jid: [] for jid in job_ids}

    if job_ids:
        results = (
            db.query(AutomationResult)
            .filter(AutomationResult.job_id.in_(job_ids))
            .order_by(AutomationResult.created_at.desc())
            .all()
        )
        for r in results:
            results_map.setdefault(r.job_id, []).append(r)

    return [_serialize_job(j, results_map.get(j.id, [])) for j in jobs]


# =========================================================
# 📋 JOB — DETALHE (COM RESULTADOS)
# =========================================================
@router.get("/jobs/{job_id}")
def detalhe_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = (
        db.query(AutomationJob)
        .filter(
            AutomationJob.id == job_id,
            AutomationJob.user_id == user.id,
        )
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    resultados = (
        db.query(AutomationResult)
        .filter(AutomationResult.job_id == job.id)
        .order_by(AutomationResult.created_at.desc())
        .all()
    )

    return _serialize_job(job, resultados)


# =========================================================
# 📥 DOWNLOAD DO RESULTADO
# =========================================================
@router.get("/results/{result_id}/download")
def download_resultado(
    result_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = (
        db.query(AutomationResult)
        .join(AutomationJob, AutomationResult.job_id == AutomationJob.id)
        .filter(
            AutomationResult.id == result_id,
            AutomationJob.user_id == user.id,
        )
        .first()
    )

    if not result:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not result.file_path:
        raise HTTPException(status_code=404, detail="Resultado não possui arquivo")

    file_path = Path(result.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    suffix = file_path.suffix.lower()
    media_type = "application/octet-stream"
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix == ".kmz":
        media_type = "application/vnd.google-earth.kmz"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )
