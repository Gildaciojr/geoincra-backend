from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db

from app.models.project import Project
from app.models.user import User

from app.schemas.ocr import (
    OcrRequest,
    OcrResponse,
)

from app.services.ocr_service import OcrService

from app.crud.document_crud import get_document

from app.crud.ocr_crud import (
    get_ocr_result,
    list_ocr_by_document,
    list_ocr_by_engine,
    list_ocr_by_pipeline,
    list_ocr_by_status,
)

from app.crud.ocr_prompt_crud import (
    get_prompt_by_id,
    get_prompt_by_slug,
    list_active_prompts,
    list_prompts_by_categoria,
    list_prompts_by_engine,
    list_prompts_by_pipeline,
    resolver_prompt_ocr,
)

router = APIRouter()


# =========================================================
# SEGURANÇA
# =========================================================
def _check_project_owner(
    db: Session,
    project_id: int,
    user_id: int,
):

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado",
        )

    return project


# =========================================================
# VALIDAR OCR
# =========================================================
def _validar_ocr_owner(
    db: Session,
    *,
    ocr_id: int,
    current_user: User,
):

    obj = get_ocr_result(db, ocr_id)

    if not obj:
        raise HTTPException(
            status_code=404,
            detail="OCR não encontrado.",
        )

    _check_project_owner(
        db,
        obj.document.project_id,
        current_user.id,
    )

    return obj


# =========================================================
# LISTAR PROMPTS OCR
# =========================================================
@router.get("/ocr/prompts")
def list_prompts(
    pipeline: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    engine: Optional[str] = Query(default=None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # =====================================================
    # PIPELINE
    # =====================================================
    if pipeline:
        return list_prompts_by_pipeline(
            db,
            pipeline=pipeline,
        )

    # =====================================================
    # CATEGORIA
    # =====================================================
    if categoria:
        return list_prompts_by_categoria(
            db,
            categoria=categoria,
        )

    # =====================================================
    # ENGINE
    # =====================================================
    if engine:
        return list_prompts_by_engine(
            db,
            engine=engine,
        )

    return list_active_prompts(db)


# =========================================================
# BUSCAR PROMPT POR ID
# =========================================================
@router.get("/ocr/prompts/{prompt_id}")
def get_prompt(
    prompt_id: int,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    prompt = get_prompt_by_id(
        db,
        prompt_id,
    )

    if not prompt:
        raise HTTPException(
            status_code=404,
            detail="Prompt OCR não encontrado.",
        )

    return prompt


# =========================================================
# BUSCAR PROMPT POR SLUG
# =========================================================
@router.get("/ocr/prompts/slug/{slug}")
def get_prompt_slug(
    slug: str,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    prompt = get_prompt_by_slug(
        db,
        slug,
    )

    if not prompt:
        raise HTTPException(
            status_code=404,
            detail="Prompt OCR não encontrado.",
        )

    return prompt


# =========================================================
# INICIAR OCR
# =========================================================
@router.post(
    "/ocr",
    response_model=OcrResponse,
)
def iniciar_ocr(
    payload: OcrRequest,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # =====================================================
    # DOCUMENTO
    # =====================================================
    doc = get_document(
        db,
        payload.document_id,
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Documento não encontrado.",
        )

    # =====================================================
    # SEGURANÇA
    # =====================================================
    _check_project_owner(
        db,
        doc.project_id,
        current_user.id,
    )

    # =====================================================
    # RESOLVER PROMPT
    # =====================================================
    prompt = resolver_prompt_ocr(
        db=db,
        prompt_id=payload.prompt_id,
        slug=payload.prompt_slug,
        pipeline=payload.pipeline,
        engine=payload.provider,
    )

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nenhum prompt OCR compatível foi encontrado."
            ),
        )

    # =====================================================
    # EXECUÇÃO OCR
    # =====================================================
    return OcrService.iniciar_ocr(
        db=db,
        document_id=payload.document_id,
        user_id=current_user.id,

        prompt_id=prompt.id,

        provider=(
            payload.provider
            or prompt.engine
            or "GOOGLE"
        ),
    )


# =========================================================
# BUSCAR RESULTADO OCR
# =========================================================
@router.get(
    "/ocr/{ocr_id}",
    response_model=OcrResponse,
)
def get_ocr(
    ocr_id: int,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return _validar_ocr_owner(
        db=db,
        ocr_id=ocr_id,
        current_user=current_user,
    )


# =========================================================
# LISTAR OCR DE UM DOCUMENTO
# =========================================================
@router.get(
    "/documents/{document_id}/ocr",
    response_model=list[OcrResponse],
)
def list_ocr_document(
    document_id: int,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    doc = get_document(
        db,
        document_id,
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Documento não encontrado.",
        )

    _check_project_owner(
        db,
        doc.project_id,
        current_user.id,
    )

    return list_ocr_by_document(
        db,
        document_id,
    )


# =========================================================
# LISTAR OCR POR PIPELINE
# =========================================================
@router.get(
    "/ocr/pipeline/{pipeline}",
    response_model=list[OcrResponse],
)
def list_ocr_pipeline(
    pipeline: str,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return list_ocr_by_pipeline(
        db,
        pipeline,
    )


# =========================================================
# LISTAR OCR POR ENGINE
# =========================================================
@router.get(
    "/ocr/engine/{engine}",
    response_model=list[OcrResponse],
)
def list_ocr_engine(
    engine: str,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return list_ocr_by_engine(
        db,
        engine,
    )


# =========================================================
# LISTAR OCR POR STATUS
# =========================================================
@router.get(
    "/ocr/status/{status}",
    response_model=list[OcrResponse],
)
def list_ocr_status(
    status: str,

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return list_ocr_by_status(
        db,
        status,
    )