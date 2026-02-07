import os
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.document import Document
from app.models.project import Project
from app.models.user import User

router = APIRouter(
    prefix="/uploads",   # ✅ CRÍTICO
    tags=["Uploads"]
)


@router.post("/matricula")
async def upload_matricula(
    project_id: int = Query(..., description="ID do projeto"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    # 🔒 Valida dono do projeto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou acesso negado",
        )

    # 🔍 Validação do arquivo
    allowed_ext = {"pdf", "jpg", "jpeg", "png"}
    if not file.filename or "." not in file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido (sem extensão).")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido.")

    # 📂 Pasta correta
    base_path = os.path.join("app", "uploads", "projects", str(project_id))
    os.makedirs(base_path, exist_ok=True)

    stored_filename = f"matricula_{int(datetime.utcnow().timestamp())}.{ext}"
    file_path = os.path.join(base_path, stored_filename)

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao salvar arquivo: {str(e)}",
        )

    # 💾 Registro no banco
    document = Document(
        project_id=project_id,
        doc_type="matricula",
        stored_filename=stored_filename,
        original_filename=file.filename,
        content_type=file.content_type,
        description="Matrícula enviada pelo usuário",
        file_path=file_path,
        uploaded_at=datetime.utcnow(),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return JSONResponse(
        {
            "message": "Matrícula enviada com sucesso",
            "document_id": document.id,
            "stored_filename": document.stored_filename,
            "original_filename": document.original_filename,
            "doc_type": document.doc_type,
            "file_path": document.file_path,
        }
    )
