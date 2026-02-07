from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.sigef_export import SigefCsvExportRequest, SigefCsvExportResponse
from app.crud.sigef_export_crud import exportar_sigef_csv
from app.models.documento_tecnico import DocumentoTecnico

router = APIRouter()


@router.post(
    "/sigef/export/csv",
    response_model=SigefCsvExportResponse,
)
def export_sigef_csv_route(
    payload: SigefCsvExportRequest,
    db: Session = Depends(get_db),
):
    try:
        data = exportar_sigef_csv(db, payload)
        return SigefCsvExportResponse(
            sucesso=True,
            mensagem="Planilha SIGEF (CSV) gerada e versionada com sucesso.",
            **data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sigef/export/{documento_tecnico_id}/download",
)
def download_sigef_csv(
    documento_tecnico_id: int,
    db: Session = Depends(get_db),
):
    """
    Download do CSV SIGEF associado a um Documento Técnico.
    """
    doc = (
        db.query(DocumentoTecnico)
        .filter(DocumentoTecnico.id == documento_tecnico_id)
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Documento técnico não encontrado.",
        )

    if not doc.arquivo_path:
        raise HTTPException(
            status_code=404,
            detail="Documento técnico não possui arquivo associado.",
        )

    path = str(doc.arquivo_path)

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Arquivo não encontrado no servidor.",
        )

    filename = os.path.basename(path)

    return FileResponse(
        path=path,
        media_type="text/csv",
        filename=filename,
    )
