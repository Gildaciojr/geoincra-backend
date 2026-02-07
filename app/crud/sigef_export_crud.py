from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.models.geometria import Geometria
from app.schemas.sigef_export import SigefCsvExportRequest
from app.services.sigef_export_service import SigefExportService
from app.schemas.documento_tecnico import DocumentoTecnicoCreate
from app.crud.documento_tecnico_crud import create_documento_tecnico


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

    epsg_origem = int(geom.epsg_origem or 4326)

    csv_str, epsg_utm, metadata = SigefExportService.gerar_csv_sigef(
        geojson=geom.geojson,
        epsg_origem=epsg_origem,
        prefixo_vertice=payload.prefixo_vertice,
    )

    arquivo_path = SigefExportService.salvar_csv_em_disco(
        imovel_id=int(geom.imovel_id),
        csv_str=csv_str,
    )

    now = datetime.utcnow()

    # Salva como Documento Técnico versionado
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
        versao=None,  # auto
    )

    doc = create_documento_tecnico(db, int(geom.imovel_id), doc_create)

    # Usa área/perímetro já calculados na geometria (se existir)
    area_ha = float(geom.area_hectares) if geom.area_hectares is not None else 0.0
    per_m = float(geom.perimetro_m) if geom.perimetro_m is not None else 0.0

    return {
        "geometria_id": int(geom.id),
        "imovel_id": int(geom.imovel_id),
        "epsg_origem": epsg_origem,
        "epsg_utm": int(epsg_utm),
        "area_hectares": area_ha,
        "perimetro_m": per_m,
        "documento_tecnico_id": int(doc.id),
        "versao": int(doc.versao),
        "arquivo_path": str(arquivo_path),
        "gerado_em": now,
        "conteudo_csv": csv_str if payload.incluir_conteudo else None,
    }
