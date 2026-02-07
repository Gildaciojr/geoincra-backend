from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.deps import get_db, get_current_user_required
from app.models.template import Template
from app.models.user import User
from app.crud.template_crud import list_templates, get_template

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("/", response_model=list)
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

    file_path = Path(template.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    return FileResponse(
        path=file_path,
        filename=template.original_filename,
        media_type="application/octet-stream",
    )
