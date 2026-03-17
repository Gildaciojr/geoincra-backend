from __future__ import annotations

import math
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.geometria import Geometria
from app.schemas.sigef_export import SigefCsvExportRequest
from app.services.sigef_export_service import SigefExportService
from app.schemas.documento_tecnico import DocumentoTecnicoCreate
from app.crud.documento_tecnico_crud import create_documento_tecnico


def _safe_float(value):
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return v
    except Exception:
        return 0.0


def _safe_int(value, default=0):
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return int(v)
    except Exception:
        return default


def exportar_sigef_csv(
    db: Session,
    payload: SigefCsvExportRequest,
) -> dict:

    geom = db.query(Geometria).filter(Geometria.id == payload.geometria_id).first()

    if not geom:
        raise ValueError("Geometria não encontrada.")

    if not geom.geojson:
        raise ValueError("Geometria sem GeoJSON.")

    if geom.imovel_id is None:
        raise ValueError("Geometria sem imovel_id.")

    # 🔥 PROTEÇÃO EPSG
    epsg_origem = _safe_int(geom.epsg_origem, 4326)

    csv_str, epsg_utm, metadata = SigefExportService.gerar_csv_sigef(
        geojson=geom.geojson,
        epsg_origem=epsg_origem,
        prefixo_vertice=payload.prefixo_vertice,
    )

    arquivo_path = SigefExportService.salvar_csv_em_disco(
        imovel_id=_safe_int(geom.imovel_id),
        csv_str=csv_str,
    )

    now = datetime.utcnow()

    doc_create = DocumentoTecnicoCreate(
        document_group_key=payload.document_group_key,
        tipo=payload.tipo,
        status_tecnico="EM_ANALISE",
        observacoes_tecnicas=payload.observacoes_tecnicas,
        conteudo_texto=None,
        conteudo_json=None,
        arquivo_path=arquivo_path,
        metadata_json=metadata,
        gerado_em=now,
        versao=None,
    )

    doc = create_documento_tecnico(db, _safe_int(geom.imovel_id), doc_create)

    area_ha = _safe_float(geom.area_hectares)
    per_m = _safe_float(geom.perimetro_m)

    return {
        "geometria_id": _safe_int(geom.id),
        "imovel_id": _safe_int(geom.imovel_id),
        "epsg_origem": epsg_origem,
        "epsg_utm": _safe_int(epsg_utm),
        "area_hectares": area_ha,
        "perimetro_m": per_m,
        "documento_tecnico_id": _safe_int(doc.id),
        "versao": _safe_int(doc.versao),
        "arquivo_path": str(arquivo_path),
        "gerado_em": now,
        "conteudo_csv": csv_str if payload.incluir_conteudo else None,
    }