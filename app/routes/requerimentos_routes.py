from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.project import Project
from app.models.template import Template
from app.crud.requerimento_crud import (
    list_by_project,
    get_by_project_and_tipo,
    upsert as upsert_req,
    delete as delete_req,
)
from app.schemas.requerimento import RequerimentoUpsert, RequerimentoOut
from app.services.docx_fill_service import fill_docx_template

router = APIRouter(
    prefix="/projects/{project_id}/requerimentos",
    tags=["Requerimentos"],
)

BASE_UPLOAD_PATH = Path("/app/app/uploads")
GENERATED_DIR = (BASE_UPLOAD_PATH / "generated").resolve()
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def _check_project_owner(db: Session, project_id: int, user_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou não pertence ao usuário",
        )
    return project


# ============================================================
# LISTAR REQUERIMENTOS DO PROJETO
# GET /api/projects/{project_id}/requerimentos
# ============================================================
@router.get("", response_model=list[RequerimentoOut])
def list_project_requerimentos(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_by_project(db, project_id)


# ============================================================
# OBTER UM REQUERIMENTO POR TIPO
# GET /api/projects/{project_id}/requerimentos/one?tipo=X
# ============================================================
@router.get("/one", response_model=RequerimentoOut)
def get_one(
    project_id: int,
    tipo: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    obj = get_by_project_and_tipo(db, project_id, tipo)
    if not obj:
        raise HTTPException(status_code=404, detail="Requerimento não encontrado")
    return obj


# ============================================================
# CRIAR / ATUALIZAR REQUERIMENTO
# PUT /api/projects/{project_id}/requerimentos
# ============================================================
@router.put("", response_model=RequerimentoOut)
def upsert_one(
    project_id: int,
    payload: RequerimentoUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    obj = upsert_req(
        db=db,
        project_id=project_id,
        tipo=payload.tipo,
        dados_json=payload.dados_json,
        template_id=payload.template_id,
        status=payload.status,
    )
    return obj


# ============================================================
# REMOVER REQUERIMENTO
# DELETE /api/projects/{project_id}/requerimentos?tipo=X
# ============================================================
@router.delete("")
def delete_one(
    project_id: int,
    tipo: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    ok = delete_req(db, project_id, tipo)
    if not ok:
        raise HTTPException(status_code=404, detail="Requerimento não encontrado")
    return {"mensagem": "Requerimento removido"}


# ============================================================
# GERAR DOCX A PARTIR DO TEMPLATE
# POST /api/projects/{project_id}/requerimentos/generate
# ============================================================
@router.post("/generate")
def generate_docx(
    project_id: int,
    tipo: str = Query(...),
    template_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    req = get_by_project_and_tipo(db, project_id, tipo)
    if not req:
        raise HTTPException(status_code=404, detail="Dados do requerimento não encontrados")

    template = (
        db.query(Template)
        .filter(Template.id == template_id, Template.ativo == True)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    template_path = Path(template.file_path).resolve()
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo do template não existe no servidor")

    out = fill_docx_template(
        template_path=template_path,
        data=req.dados_json,
        output_dir=GENERATED_DIR,
    )

    return FileResponse(
        path=str(out),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{tipo}_{project_id}.docx",
    )
