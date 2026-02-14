from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
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
# 🤖 JOB — CONSULTAR MATRÍCULAS (RI DIGITAL)
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

    return {
        "job_id": job.id,
        "status": job.status,
    }


# =========================================================
# 📋 JOBS — LISTAGEM E DETALHE
# =========================================================

@router.get("/jobs")
def listar_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    jobs = (
        db.query(AutomationJob)
        .filter(AutomationJob.user_id == user.id)
        .order_by(AutomationJob.created_at.desc())
        .all()
    )

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
        .all()
    )

    return {
        "job": job,
        "resultados": resultados,
    }


# =========================================================
# 📥 DOWNLOAD DO PDF
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

    return {
        "file_path": result.file_path
    }
