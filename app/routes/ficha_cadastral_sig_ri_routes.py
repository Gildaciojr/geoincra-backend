from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.imovel import Imovel
from app.models.user import User
from app.services.ficha_cadastral_sig_ri_service import (
    FichaCadastralSigRiService,
)


router = APIRouter(
    prefix="/ficha-cadastral-sig-ri",
    tags=["Ficha Cadastral SIG-RI"],
)


class FichaCadastralSigRiRequest(BaseModel):
    observacoes_tecnicas: Optional[str] = None


@router.get("/imoveis/{imovel_id}/preview")
def preview_ficha_cadastral_sig_ri(
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    imovel = db.get(Imovel, imovel_id)

    if not imovel:
        raise HTTPException(
            status_code=404,
            detail="Imóvel não encontrado.",
        )

    if imovel.project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado ao imóvel informado.",
        )

    try:
        payload = FichaCadastralSigRiService.montar_payload(
            db=db,
            imovel_id=imovel_id,
        )

        texto = FichaCadastralSigRiService.renderizar_texto(
            payload,
        )

        return {
            "sucesso": True,
            "imovel_id": imovel_id,
            "payload": payload,
            "conteudo_texto": texto,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao montar ficha SIG-RI: {str(exc)}",
        )


@router.post("/imoveis/{imovel_id}/gerar")
def gerar_ficha_cadastral_sig_ri(
    imovel_id: int,
    payload: FichaCadastralSigRiRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    imovel = db.get(Imovel, imovel_id)

    if not imovel:
        raise HTTPException(
            status_code=404,
            detail="Imóvel não encontrado.",
        )

    if imovel.project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado ao imóvel informado.",
        )

    try:
        documento = FichaCadastralSigRiService.gerar_documento_tecnico(
            db=db,
            imovel_id=imovel_id,
            observacoes_tecnicas=payload.observacoes_tecnicas,
        )

        return {
            "sucesso": True,
            "mensagem": "Ficha Cadastral SIG-RI gerada com sucesso.",
            "documento_tecnico_id": documento.id,
            "imovel_id": documento.imovel_id,
            "document_group_key": documento.document_group_key,
            "tipo": documento.tipo,
            "status_tecnico": documento.status_tecnico,
            "versao": documento.versao,
            "conteudo_json": documento.conteudo_json,
            "conteudo_texto": documento.conteudo_texto,
            "gerado_em": documento.gerado_em,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar ficha SIG-RI: {str(exc)}",
        )