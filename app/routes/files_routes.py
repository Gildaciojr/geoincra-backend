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
# DOWNLOAD DE DOCUMENTOS DO PROJETO (PROTEGIDO)
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

    if doc.project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    file_path = (BASE_UPLOAD_PATH / doc.file_path).resolve()

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    return FileResponse(
        path=file_path,
        media_type=doc.content_type or "application/octet-stream",
        filename=doc.original_filename or file_path.name,
    )


# =========================================================
# DOWNLOAD DE PDF (ORÇAMENTOS / PROPOSTAS / CONTRATOS)
# =========================================================
@router.get("/pdf")
def download_pdf(
    path: str = Query(...),
    db: Session = Depends(get_db),
):
    # =========================================================
    # 🔒 NORMALIZA CAMINHO (ANTI PATH TRAVERSAL)
    # =========================================================
    file_path = (BASE_UPLOAD_PATH / path).resolve()

    if not str(file_path).startswith(str(BASE_UPLOAD_PATH)):
        raise HTTPException(status_code=403, detail="Caminho inválido")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # =========================================================
    # 🔒 VALIDAÇÃO DE ESTRUTURA
    # =========================================================
    parts = Path(path).parts

    if len(parts) < 3:
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    # 🔥 PERMITE MÚLTIPLOS TIPOS CONTROLADOS
    tipo_pasta = parts[0]

    if tipo_pasta not in [
        "propostas",
        "orcamentos",
        # pronto para expansão futura:
        # "contratos",
        # "relatorios",
    ]:
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    # =========================================================
    # 🔒 VALIDA project_id
    # =========================================================
    project_folder = parts[1]

    if not project_folder.startswith("project_"):
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    project_id_str = project_folder.replace("project_", "")

    if not project_id_str.isdigit():
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    project_id = int(project_id_str)

    # =========================================================
    # 🔒 GARANTE EXISTÊNCIA DO PROJETO
    # =========================================================
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # =========================================================
    # 📄 RETORNO DO ARQUIVO
    # =========================================================
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )