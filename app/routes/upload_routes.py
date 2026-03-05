# app/routes/upload_routes.py

from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Query,
    Depends,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.document import Document
from app.models.project import Project
from app.models.user import User

from app.services.document_folder_resolver import resolve_project_folder


router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)

# ==========================================================
# BASE UPLOAD (DOCKER / LOCAL)
# ==========================================================

DOCKER_BASE_UPLOAD = Path("/app/app/uploads")
LOCAL_BASE_UPLOAD = Path("app/uploads")


def _resolve_base_upload_dir() -> Path:
    """
    Resolve o diretório base de uploads dependendo do ambiente.

    Docker:
        /app/app/uploads

    Desenvolvimento local:
        app/uploads
    """
    if DOCKER_BASE_UPLOAD.exists():
        return DOCKER_BASE_UPLOAD

    return LOCAL_BASE_UPLOAD


# ==========================================================
# UPLOAD GENÉRICO DE DOCUMENTO
# ==========================================================

@router.post("/document")
async def upload_document(
    project_id: int = Query(...),
    doc_type: str = Query(..., description="Categoria do documento"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):

    # ======================================================
    # VALIDAÇÃO MULTIUSUÁRIO
    # ======================================================

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou acesso negado",
        )

    # ======================================================
    # VALIDAÇÃO DO ARQUIVO
    # ======================================================

    if not file.filename or "." not in file.filename:
        raise HTTPException(
            status_code=400,
            detail="Arquivo inválido.",
        )

    allowed_ext = {
        "pdf",
        "jpg",
        "jpeg",
        "png",
        "doc",
        "docx",
    }

    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido.",
        )

    # ======================================================
    # RESOLVER DIRETÓRIO BASE
    # ======================================================

    base_dir = _resolve_base_upload_dir()

    # ======================================================
    # RESOLVER PASTA DO DOCUMENTO
    # ======================================================

    folder = resolve_project_folder(doc_type)

    project_dir = (
        base_dir
        / "projects"
        / f"project_{project_id}"
        / folder
    )

    project_dir.mkdir(parents=True, exist_ok=True)

    # ======================================================
    # GERAR NOME DO ARQUIVO
    # ======================================================

    timestamp = int(datetime.utcnow().timestamp())

    stored_filename = f"{doc_type}_{timestamp}.{ext}"

    absolute_file_path = project_dir / stored_filename

    # ======================================================
    # SALVAR ARQUIVO
    # ======================================================

    try:

        content = await file.read()

        with open(absolute_file_path, "wb") as f:
            f.write(content)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Falha ao salvar arquivo: {str(e)}",
        )

    # ======================================================
    # CAMINHO RELATIVO PARA BANCO
    # ======================================================

    relative_path = (
        f"projects/project_{project_id}/{folder}/{stored_filename}"
    )

    # ======================================================
    # REGISTRAR DOCUMENTO NO BANCO
    # ======================================================

    document = Document(
        project_id=project_id,
        doc_type=doc_type,
        stored_filename=stored_filename,
        original_filename=file.filename,
        content_type=file.content_type,
        description=f"Documento do tipo {doc_type}",
        file_path=relative_path,
        uploaded_at=datetime.utcnow(),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # ======================================================
    # RESPOSTA
    # ======================================================

    return JSONResponse(
        {
            "message": "Documento enviado com sucesso",
            "document_id": document.id,
            "doc_type": document.doc_type,
            "file_path": document.file_path,
            "download_url": f"/api/files/documents/{document.id}",
        }
    )