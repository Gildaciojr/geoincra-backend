# geoincra_backend/app/routes/upload_routes.py
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.document import Document
from app.models.project import Project
from app.models.user import User

from app.crud.timeline_crud import create_timeline_entry
from app.schemas.timeline import TimelineCreate

router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)

# ✅ Base padrão no Docker (alinhado com files_routes.py)
DOCKER_BASE_UPLOAD = Path("/app/app/uploads")

# ✅ Fallback local (dev sem docker)
LOCAL_BASE_UPLOAD = Path("app/uploads")


def _resolve_base_upload_dir() -> Path:
    # se existir no container, usa o path do docker
    if DOCKER_BASE_UPLOAD.exists():
        return DOCKER_BASE_UPLOAD
    return LOCAL_BASE_UPLOAD


@router.post("/matricula")
async def upload_matricula(
    project_id: int = Query(..., description="ID do projeto"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    # 🔒 Valida dono do projeto (multiusuário)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou acesso negado",
        )

    # 🔍 Validação do arquivo
    allowed_ext = {"pdf", "jpg", "jpeg", "png"}
    if not file.filename or "." not in file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido (sem extensão).")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido.")

    # 📂 Pasta correta (alinhada ao /files/documents/{id})
    base_upload_dir = _resolve_base_upload_dir()
    project_dir = base_upload_dir / "projects" / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"matricula_{int(datetime.utcnow().timestamp())}.{ext}"
    absolute_file_path = project_dir / stored_filename

    # 💾 Salvar arquivo
    try:
        content = await file.read()
        with open(absolute_file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao salvar arquivo: {str(e)}")

    # 💾 Registro no banco
    document = Document(
        project_id=project_id,
        doc_type="matricula",
        stored_filename=stored_filename,
        original_filename=file.filename,
        content_type=file.content_type,
        description="Matrícula enviada pelo usuário",
        file_path=str(absolute_file_path),  # ✅ absoluto = download sempre funciona
        uploaded_at=datetime.utcnow(),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # 🧾 Timeline (com fallback seguro pra não quebrar se o schema mudar)
    try:
        # tentativa 1: padrão "stage/status/progress" (compatível com seu frontend)
        create_timeline_entry(
            db=db,
            project_id=project_id,
            payload=TimelineCreate(
                stage="Upload de Documentos",
                status="Concluído",
                progress=10,
                notes=f"Matrícula enviada: {file.filename}",
            ),
        )
    except TypeError:
        # tentativa 2: padrão "tipo/descricao" (se seu schema for desse estilo)
        try:
            create_timeline_entry(
                db=db,
                project_id=project_id,
                payload=TimelineCreate(
                    tipo="UPLOAD_DOCUMENTO",
                    descricao=f"Matrícula enviada: {file.filename}",
                ),
            )
        except Exception:
            # não derruba o upload por falha de timeline
            pass
    except Exception:
        pass

    # ✅ URL segura (precisa Authorization no download)
    download_url = f"/api/files/documents/{document.id}"

    return JSONResponse(
        {
            "message": "Matrícula enviada com sucesso",
            "document_id": document.id,
            "stored_filename": document.stored_filename,
            "original_filename": document.original_filename,
            "doc_type": document.doc_type,
            "file_path": document.file_path,
            "download_url": download_url,  
        }
    )
