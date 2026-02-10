from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.crud.template_crud import list_templates, get_template, create_template
from app.schemas.template import TemplateResponse, TemplateCreate

router = APIRouter(prefix="/templates", tags=["Templates"])

# =========================================================
# PATH BASE (Docker + Dev)
# =========================================================
DOCKER_BASE_UPLOAD = Path("/app/app/uploads")
LOCAL_BASE_UPLOAD = Path("app/uploads")


def _resolve_base_upload_dir() -> Path:
    if DOCKER_BASE_UPLOAD.exists():
        return DOCKER_BASE_UPLOAD
    return LOCAL_BASE_UPLOAD


BASE_TEMPLATES_PATH = (_resolve_base_upload_dir() / "templates").resolve()
BASE_TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)


# =========================================================
# LIST
# =========================================================
@router.get("/", response_model=list[TemplateResponse])
def list_templates_route(
    categoria: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    return list_templates(db, categoria)


# =========================================================
# DOWNLOAD
# =========================================================
@router.get("/{template_id}/download")
def download_template_route(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    template = get_template(db, template_id)
    if not template or not template.ativo:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    file_path = Path(template.file_path).resolve()

    if not str(file_path).startswith(str(BASE_TEMPLATES_PATH)):
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    return FileResponse(
        path=str(file_path),
        filename=template.original_filename,
        media_type="application/octet-stream",
    )


# =========================================================
# UPLOAD TEMPLATE
# =========================================================
@router.post("/upload", response_model=TemplateResponse)
async def upload_template_route(
    nome: str = Query(...),
    categoria: str = Query(...),
    descricao: str | None = Query(None),
    versao: str | None = Query(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):

    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    ext = file.filename.split(".")[-1]
    stored_filename = f"template_{int(datetime.utcnow().timestamp())}.{ext}"

    absolute_file_path = BASE_TEMPLATES_PATH / stored_filename

    content = await file.read()
    with open(absolute_file_path, "wb") as f:
        f.write(content)

    template = create_template(
        db,
        TemplateCreate(
            nome=nome,
            descricao=descricao,
            categoria=categoria,
            versao=versao,
            stored_filename=stored_filename,
            original_filename=file.filename,
            file_path=str(absolute_file_path),
        ),
    )

    return template
