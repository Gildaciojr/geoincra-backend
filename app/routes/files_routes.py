from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.deps import get_db, get_current_user_required
from app.models.document import Document
from app.models.project import Project
from app.models.user import User

router = APIRouter(prefix="/files", tags=["Arquivos"])

# Base uploads (docker)
BASE_UPLOAD_PATH = Path("/app/app/uploads").resolve()


# =========================================================
# DOWNLOAD DE DOCUMENTOS DO PROJETO
# =========================================================
@router.get("/documents/{document_id}")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # valida dono
    if doc.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    file_path = Path(doc.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    return FileResponse(
        path=file_path,
        media_type=doc.content_type or "application/octet-stream",
        filename=doc.original_filename or file_path.name,
    )


# =========================================================
# DOWNLOAD DE PDF DE PROPOSTAS / CONTRATOS (PROTEGIDO)
# =========================================================
@router.get("/pdf")
def download_pdf(
    path: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    # protege contra path traversal
    file_path = (BASE_UPLOAD_PATH / path).resolve()

    if not str(file_path).startswith(str(BASE_UPLOAD_PATH)):
        raise HTTPException(status_code=403, detail="Acesso inválido")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # ✅ Proteção multiusuário: exige que PDF esteja dentro de /propostas/project_{id}/...
    parts = Path(path).parts
    # esperado: ("propostas", "project_{id}", "arquivo.pdf")
    if len(parts) < 3 or parts[0] != "propostas" or not str(parts[1]).startswith("project_"):
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    project_id_str = str(parts[1]).replace("project_", "").strip()
    if not project_id_str.isdigit():
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    project_id = int(project_id_str)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )
