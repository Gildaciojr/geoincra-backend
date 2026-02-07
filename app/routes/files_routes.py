from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/files", tags=["Arquivos"])

BASE_PATH = Path("/app/app/uploads")

@router.get("/pdf")
def download_pdf(path: str):
    file_path = BASE_PATH / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_path.name,
    )
