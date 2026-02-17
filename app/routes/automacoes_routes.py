# geoincra_backend/app/routes/automacoes_routes.py
from __future__ import annotations

from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.external_credential import ExternalCredential
from app.models.automation_job import AutomationJob
from app.models.automation_result import AutomationResult

router = APIRouter(prefix="/automacoes")


# =========================================================
# 🔐 CREDENCIAIS — RI DIGITAL
# =========================================================
@router.post("/credenciais/ri-digital")
def salvar_credenciais_ri_digital(
    login: str,
    senha: str,
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
        cred.login = login
        cred.password_encrypted = senha
        cred.active = True
    else:
        cred = ExternalCredential(
            user_id=user.id,
            provider="RI_DIGITAL",
            login=login,
            password_encrypted=senha,
            active=True,
        )
        db.add(cred)

    db.commit()

    return {
        "provider": "RI_DIGITAL",
        "login": login[:3] + "***",
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
        "login": cred.login[:3] + "***",
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
# 🤖 JOB — RI DIGITAL (MATRÍCULAS)
# =========================================================
@router.post("/ri-digital/matriculas/jobs")
def criar_job_consulta_matriculas(
    data_inicio: str,
    data_fim: str,
    project_id: int | None = None,
    usar_credencial_salva: bool = True,
    login: str | None = None,
    senha: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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

    return {"job_id": str(job.id), "status": job.status}


# =========================================================
# 🤖 JOB — ONR / SIG-RI (CONSULTA)
# - OBRIGATÓRIO project_id (multiusuário + vínculo)
# - modo: "CAR" ou "ENDERECO"
# - valor: car ou texto do endereço
# =========================================================
@router.post("/onr/consulta/jobs")
def criar_job_onr_consulta(
    project_id: int,
    modo: str,
    valor: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 🔒 valida projeto e dono (multiusuário)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado ou acesso negado")

    modo_norm = (modo or "").upper().strip()
    if modo_norm not in {"CAR", "ENDERECO"}:
        raise HTTPException(status_code=400, detail="Modo inválido. Use CAR ou ENDERECO")

    valor_norm = (valor or "").strip()
    if len(valor_norm) < 3:
        raise HTTPException(status_code=400, detail="Valor inválido para consulta")

    job = AutomationJob(
        user_id=user.id,
        project_id=project_id,
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

    return {"job_id": str(job.id), "status": job.status}


# =========================================================
# 📋 JOBS — LISTAGEM E DETALHE
# =========================================================
@router.get("/jobs")
def listar_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    type: str | None = Query(None, description="Filtro opcional: RI_DIGITAL_MATRICULA | ONR_SIGRI_CONSULTA"),
):
    q = db.query(AutomationJob).filter(AutomationJob.user_id == user.id)
    if type:
        q = q.filter(AutomationJob.type == type)
    jobs = q.order_by(AutomationJob.created_at.desc()).all()
    return jobs


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

    return {"job": job, "resultados": resultados}


# =========================================================
# 📥 DOWNLOAD SEGURO DO ARQUIVO DO RESULTADO
# (PDF RI Digital / KMZ ONR)
# - valida dono via job.user_id
# - não expõe path sem permissão
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

    file_path = Path(result.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    # Filename “bonito” para download
    filename = file_path.name
    media_type = "application/octet-stream"
    if filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.lower().endswith(".kmz"):
        media_type = "application/vnd.google-earth.kmz"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
