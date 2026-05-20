from typing import Optional

from sqlalchemy.orm import Query, Session

from app.models.ocr_prompt import OcrPrompt


# =========================================================
# BASE QUERY
# =========================================================
def _base_prompt_query(db: Session) -> Query:
    return db.query(OcrPrompt)


# =========================================================
# PROMPT POR ID
# =========================================================
def get_prompt_by_id(
    db: Session,
    prompt_id: int,
) -> Optional[OcrPrompt]:

    return (
        _base_prompt_query(db)
        .filter(OcrPrompt.id == prompt_id)
        .first()
    )


# =========================================================
# PROMPT POR SLUG
# =========================================================
def get_prompt_by_slug(
    db: Session,
    slug: str,
) -> Optional[OcrPrompt]:

    slug_normalizado = str(slug).strip().lower()

    if not slug_normalizado:
        return None

    return (
        _base_prompt_query(db)
        .filter(OcrPrompt.slug == slug_normalizado)
        .first()
    )


# =========================================================
# LISTAR PROMPTS ATIVOS
# =========================================================
def list_active_prompts(
    db: Session,
):

    return (
        _base_prompt_query(db)
        .filter(OcrPrompt.ativo.is_(True))
        .filter(OcrPrompt.exibir_frontend.is_(True))
        .order_by(
            OcrPrompt.ordem_exibicao.asc(),
            OcrPrompt.prioridade.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )


# =========================================================
# LISTAR POR PIPELINE
# =========================================================
def list_prompts_by_pipeline(
    db: Session,
    pipeline: str,
    *,
    somente_ativos: bool = True,
):

    query = (
        _base_prompt_query(db)
        .filter(
            OcrPrompt.pipeline == str(pipeline).strip().upper()
        )
    )

    if somente_ativos:
        query = query.filter(OcrPrompt.ativo.is_(True))

    return (
        query.order_by(
            OcrPrompt.prioridade.desc(),
            OcrPrompt.versao.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )


# =========================================================
# LISTAR POR CATEGORIA
# =========================================================
def list_prompts_by_categoria(
    db: Session,
    categoria: str,
    *,
    somente_ativos: bool = True,
):

    query = (
        _base_prompt_query(db)
        .filter(
            OcrPrompt.categoria == str(categoria).strip().upper()
        )
    )

    if somente_ativos:
        query = query.filter(OcrPrompt.ativo.is_(True))

    return (
        query.order_by(
            OcrPrompt.prioridade.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )


# =========================================================
# LISTAR POR ENGINE
# =========================================================
def list_prompts_by_engine(
    db: Session,
    engine: str,
    *,
    somente_ativos: bool = True,
):

    query = (
        _base_prompt_query(db)
        .filter(
            OcrPrompt.engine == str(engine).strip().upper()
        )
    )

    if somente_ativos:
        query = query.filter(OcrPrompt.ativo.is_(True))

    return (
        query.order_by(
            OcrPrompt.pipeline.asc(),
            OcrPrompt.prioridade.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )


# =========================================================
# RESOLVER PROMPT OCR
# =========================================================
def resolver_prompt_ocr(
    db: Session,
    *,
    prompt_id: Optional[int] = None,
    slug: Optional[str] = None,
    pipeline: Optional[str] = None,
    engine: Optional[str] = None,
) -> Optional[OcrPrompt]:

    # =====================================================
    # PRIORIDADE 1 — ID
    # =====================================================
    if prompt_id:

        prompt = get_prompt_by_id(
            db,
            prompt_id,
        )

        if prompt and prompt.ativo:
            return prompt

    # =====================================================
    # PRIORIDADE 2 — SLUG
    # =====================================================
    if slug:

        prompt = get_prompt_by_slug(
            db,
            slug,
        )

        if prompt and prompt.ativo:
            return prompt

    # =====================================================
    # PRIORIDADE 3 — PIPELINE + ENGINE
    # =====================================================
    query = _base_prompt_query(db)

    query = query.filter(
        OcrPrompt.ativo.is_(True)
    )

    if pipeline:
        query = query.filter(
            OcrPrompt.pipeline
            == str(pipeline).strip().upper()
        )

    if engine:
        query = query.filter(
            OcrPrompt.engine
            == str(engine).strip().upper()
        )

    prompt = (
        query.order_by(
            OcrPrompt.prioridade.desc(),
            OcrPrompt.versao.desc(),
            OcrPrompt.id.desc(),
        )
        .first()
    )

    return prompt


# =========================================================
# PROMPTS COM GEOMETRIA
# =========================================================
def list_prompts_geometria(
    db: Session,
):

    return (
        _base_prompt_query(db)
        .filter(OcrPrompt.ativo.is_(True))
        .filter(OcrPrompt.habilitar_pipeline_geometrico.is_(True))
        .order_by(
            OcrPrompt.prioridade.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )


# =========================================================
# PROMPTS REGISTRAIS
# =========================================================
def list_prompts_registrais(
    db: Session,
):

    return (
        _base_prompt_query(db)
        .filter(OcrPrompt.ativo.is_(True))
        .filter(OcrPrompt.habilitar_pipeline_registral.is_(True))
        .order_by(
            OcrPrompt.prioridade.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )


# =========================================================
# PROMPTS CONFRONTANTES
# =========================================================
def list_prompts_confrontantes(
    db: Session,
):

    return (
        _base_prompt_query(db)
        .filter(OcrPrompt.ativo.is_(True))
        .filter(OcrPrompt.habilitar_pipeline_confrontantes.is_(True))
        .order_by(
            OcrPrompt.prioridade.desc(),
            OcrPrompt.nome.asc(),
        )
        .all()
    )