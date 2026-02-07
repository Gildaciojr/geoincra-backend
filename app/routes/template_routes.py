from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.crud.template_crud import list_templates, get_template
from app.schemas.template import TemplateResponse

router = APIRouter(prefix="/templates", tags=["Templates"])

# Base segura para arquivos de templates
BASE_TEMPLATES_PATH = Path("app/uploads/templates").resolve()


@router.get("/", response_model=list[TemplateResponse])
def list_templates_route(
    categoria: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    return list_templates(db, categoria)


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

    # 🔒 proteção contra acesso fora da pasta de templates
    if not str(file_path).startswith(str(BASE_TEMPLATES_PATH)):
        raise HTTPException(status_code=403, detail="Acesso inválido ao arquivo")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    return FileResponse(
        path=file_path,
        filename=template.original_filename,
        media_type="application/octet-stream",
    )
