from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Query, Session

from app.models.ocr_result import OcrResult


# =========================================================
# BASE QUERY
# =========================================================
def _base_ocr_query(db: Session) -> Query:
    return db.query(OcrResult)


# =========================================================
# OCR POR ID
# =========================================================
def get_ocr_result(
    db: Session,
    ocr_id: int,
) -> Optional[OcrResult]:

    return (
        _base_ocr_query(db)
        .filter(OcrResult.id == ocr_id)
        .first()
    )


# =========================================================
# OCR MAIS RECENTE DO DOCUMENTO
# =========================================================
def get_latest_ocr_by_document(
    db: Session,
    document_id: int,
) -> Optional[OcrResult]:

    return (
        _base_ocr_query(db)
        .filter(OcrResult.document_id == document_id)
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .first()
    )


# =========================================================
# LISTAR OCR POR DOCUMENTO
# =========================================================
def list_ocr_by_document(
    db: Session,
    document_id: int,
):

    return (
        _base_ocr_query(db)
        .filter(OcrResult.document_id == document_id)
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# LISTAR OCR POR STATUS
# =========================================================
def list_ocr_by_status(
    db: Session,
    status: str,
):

    return (
        _base_ocr_query(db)
        .filter(
            OcrResult.status
            == str(status).strip().upper()
        )
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# LISTAR OCR POR PIPELINE
# =========================================================
def list_ocr_by_pipeline(
    db: Session,
    pipeline: str,
):

    return (
        _base_ocr_query(db)
        .filter(
            OcrResult.pipeline
            == str(pipeline).strip().upper()
        )
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# LISTAR OCR POR ENGINE
# =========================================================
def list_ocr_by_engine(
    db: Session,
    engine: str,
):

    return (
        _base_ocr_query(db)
        .filter(
            OcrResult.engine
            == str(engine).strip().upper()
        )
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# OCR COM GEOJSON
# =========================================================
def list_ocr_com_geojson(
    db: Session,
):

    return (
        _base_ocr_query(db)
        .filter(OcrResult.possui_geojson.is_(True))
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# OCR COM ERRO
# =========================================================
def list_ocr_com_erro(
    db: Session,
):

    return (
        _base_ocr_query(db)
        .filter(
            OcrResult.status == "ERROR"
        )
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# OCR PROCESSADOS COM SUCESSO
# =========================================================
def list_ocr_success(
    db: Session,
):

    return (
        _base_ocr_query(db)
        .filter(
            OcrResult.status == "DONE"
        )
        .order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .all()
    )


# =========================================================
# OCR PENDENTES
# =========================================================
def list_ocr_pending(
    db: Session,
):

    return (
        _base_ocr_query(db)
        .filter(
            OcrResult.status.in_(
                [
                    "PENDING",
                    "PROCESSING",
                ]
            )
        )
        .order_by(
            OcrResult.created_at.asc(),
            OcrResult.id.asc(),
        )
        .all()
    )


# =========================================================
# BUSCA TÉCNICA OCR
# =========================================================
def search_ocr_results(
    db: Session,
    *,
    document_id: Optional[int] = None,
    pipeline: Optional[str] = None,
    engine: Optional[str] = None,
    status: Optional[str] = None,
    possui_geojson: Optional[bool] = None,
    possui_confrontantes: Optional[bool] = None,
    possui_historico: Optional[bool] = None,
    limit: int = 100,
):

    query = _base_ocr_query(db)

    if document_id is not None:
        query = query.filter(
            OcrResult.document_id == document_id
        )

    if pipeline:
        query = query.filter(
            OcrResult.pipeline
            == str(pipeline).strip().upper()
        )

    if engine:
        query = query.filter(
            OcrResult.engine
            == str(engine).strip().upper()
        )

    if status:
        query = query.filter(
            OcrResult.status
            == str(status).strip().upper()
        )

    if possui_geojson is not None:
        query = query.filter(
            OcrResult.possui_geojson.is_(possui_geojson)
        )

    if possui_confrontantes is not None:
        query = query.filter(
            OcrResult.possui_confrontantes.is_(
                possui_confrontantes
            )
        )

    if possui_historico is not None:
        query = query.filter(
            OcrResult.possui_historico_registral.is_(
                possui_historico
            )
        )

    return (
        query.order_by(
            OcrResult.created_at.desc(),
            OcrResult.id.desc(),
        )
        .limit(limit)
        .all()
    )


# =========================================================
# RESUMO OCR
# =========================================================
def gerar_resumo_ocr(
    ocr: OcrResult,
) -> Dict[str, Any]:

    dados = ocr.dados_extraidos_json or {}

    return {
        "ocr_id": ocr.id,
        "document_id": ocr.document_id,
        "status": ocr.status,
        "pipeline": ocr.pipeline,
        "engine": ocr.engine,
        "provider": ocr.provider,
        "modelo_llm": ocr.modelo_llm,
        "possui_geojson": ocr.possui_geojson,
        "possui_memorial": ocr.possui_memorial,
        "possui_confrontantes": ocr.possui_confrontantes,
        "possui_historico_registral": (
            ocr.possui_historico_registral
        ),
        "score_qualidade": ocr.score_qualidade,
        "tempo_processamento_ms": (
            ocr.tempo_processamento_ms
        ),
        "created_at": ocr.created_at,
        "updated_at": ocr.updated_at,
        "erro": ocr.erro,
        "dados_extraidos": dados,
    }


# =========================================================
# RESUMO EM LOTE
# =========================================================
def gerar_resumo_lote_ocr(
    resultados: List[OcrResult],
) -> List[Dict[str, Any]]:

    return [
        gerar_resumo_ocr(item)
        for item in resultados
    ]