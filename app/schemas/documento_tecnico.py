from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# =========================================================
# BASE
# =========================================================
class DocumentoTecnicoBase(BaseModel):
    document_group_key: str = Field(..., min_length=2, max_length=80)
    tipo: str = Field(..., min_length=2, max_length=120)

    # RASCUNHO | EM_ANALISE | APROVADO | CORRIGIR | REPROVADO
    status_tecnico: str = Field(default="RASCUNHO", min_length=2, max_length=30)

    observacoes_tecnicas: Optional[str] = None

    conteudo_texto: Optional[str] = None
    conteudo_json: Optional[Dict[str, Any]] = None

    arquivo_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    gerado_em: Optional[datetime] = None


# =========================================================
# CREATE
# =========================================================
class DocumentoTecnicoCreate(DocumentoTecnicoBase):
    # Se não informar, começa em 1 (primeira versão)
    versao: Optional[int] = Field(default=None, ge=1)


# =========================================================
# UPDATE
# =========================================================
class DocumentoTecnicoUpdate(BaseModel):
    tipo: Optional[str] = Field(default=None, min_length=2, max_length=120)
    status_tecnico: Optional[str] = Field(default=None, min_length=2, max_length=30)
    observacoes_tecnicas: Optional[str] = None

    conteudo_texto: Optional[str] = None
    conteudo_json: Optional[Dict[str, Any]] = None

    arquivo_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    gerado_em: Optional[datetime] = None


# =========================================================
# RESPONSE
# =========================================================
class DocumentoTecnicoResponse(DocumentoTecnicoBase):
    id: int
    imovel_id: int

    versao: int
    is_versao_atual: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================================================
# VERSIONAMENTO (CRIAR NOVA VERSÃO)
# =========================================================
class DocumentoTecnicoNovaVersaoRequest(BaseModel):
    # Se não mandar, mantém o mesmo tipo do documento anterior
    tipo: Optional[str] = Field(default=None, min_length=2, max_length=120)

    status_tecnico: str = Field(default="RASCUNHO", min_length=2, max_length=30)
    observacoes_tecnicas: Optional[str] = None

    conteudo_texto: Optional[str] = None
    conteudo_json: Optional[Dict[str, Any]] = None

    arquivo_path: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    gerado_em: Optional[datetime] = None
