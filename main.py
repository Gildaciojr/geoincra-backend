from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

import time
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.database import Base, engine
from app.routes.auth_routes import router as auth_router


# ============================================================
# IMPORTAÇÃO DOS MODELS
# ============================================================

import app.models.user
import app.models.project
import app.models.project_status
import app.models.project_marco
import app.models.timeline

import app.models.imovel
import app.models.matricula
import app.models.proprietario
import app.models.municipio
import app.models.cartorio
import app.models.confrontante

import app.models.document
import app.models.documento_tecnico
import app.models.documento_tecnico_checklist

import app.models.geometria
import app.models.sobreposicao

import app.models.pagamento
import app.models.parcela_pagamento
import app.models.pagamento_evento

import app.models.audit_log

import app.models.profissional
import app.models.proposta_profissional
import app.models.projeto_profissional
import app.models.profissional_selecao
import app.models.profissional_ranking
import app.models.avaliacao_profissional

import app.models.calculation_parameter
import app.models.proposal
import app.models.ocr_result
import app.models.template


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="GeoINCRA Backend",
    version="1.0.0",
    description="Plataforma de Automação do Processo de Georreferenciamento Rural",
)

# ============================================================
# 🔐 SWAGGER AUTH (Bearer JWT)
# ============================================================

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# ============================================================
# STARTUP EVENT — GARANTE BANCO DISPONÍVEL
# ============================================================

@app.on_event("startup")
def startup_event():
    retries = 10
    while retries:
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Banco conectado e tabelas garantidas")
            break
        except OperationalError:
            retries -= 1
            print("⏳ Aguardando banco de dados...")
            time.sleep(2)

    if not retries:
        raise RuntimeError("❌ Banco de dados não ficou disponível")

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# IMPORTAÇÃO DAS ROTAS
# ============================================================

from app.routes.health import router as health_router
from app.routes.user_routes import router as user_router
from app.routes.auth_routes import router as auth_router

from app.routes.project_routes import router as project_router
from app.routes.project_status_routes import router as project_status_router
from app.routes.project_marcos_routes import router as project_marcos_router
from app.routes.project_automacao_routes import router as project_automacao_router

# ✅ NOVAS ROTAS CORRETAS
from app.routes.imovel_routes import router as imovel_router
from app.routes.matricula_routes import router as matricula_router

from app.routes.requerimentos_routes import router as requerimentos_router
from app.routes.document_routes import router as document_router
from app.routes.documento_tecnico_routes import router as documento_tecnico_router
from app.routes.documento_tecnico_checklist_routes import (
    router as documento_tecnico_checklist_router,
)

from app.routes.geometria_routes import router as geometria_router
from app.routes.sobreposicao_routes import router as sobreposicao_router
from app.routes.memorial_routes import router as memorial_router
from app.routes.croqui_routes import router as croqui_router

from app.routes.cartorio_routes import router as cartorio_router
from app.routes.municipio_routes import router as municipio_router
from app.routes.confrontante_routes import router as confrontante_router

from app.routes.timeline_routes import router as timeline_router
from app.routes.upload_routes import router as upload_router
from app.routes import files_routes

from app.routes.calculation_routes import router as calculation_router
from app.routes.calculation_parameter_routes import router as calculation_parameter_router

from app.routes.proposal_routes import router as proposal_router
from app.routes.pagamento_routes import router as pagamento_router
from app.routes.checkout_routes import router as checkout_router
from app.routes.pagamento_webhook_routes import router as webhook_router

from app.routes.profissional_routes import router as profissional_router
from app.routes.proposta_profissional_routes import router as proposta_profissional_router
from app.routes.projeto_profissional_routes import router as projeto_profissional_router
from app.routes.profissional_selecao_routes import router as profissional_selecao_router
from app.routes.profissional_avaliacao_routes import router as profissional_avaliacao_router
from app.routes.profissional_ranking_routes import router as profissional_ranking_router

from app.routes.audit_log_routes import router as audit_log_router
from app.routes.sigef_export_routes import router as sigef_export_router
from app.routes.map_routes import router as map_router

from app.routes.template_routes import router as template_router


# ============================================================
# ROTAS
# ============================================================

app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(user_router, prefix="/api/users", tags=["Users"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

app.include_router(project_router, prefix="/api", tags=["Projects"])
app.include_router(project_status_router, prefix="/api", tags=["Project Status"])
app.include_router(project_marcos_router, prefix="/api", tags=["Project Marcos"])
app.include_router(project_automacao_router, prefix="/api", tags=["Project Automação"])

# ✅ ROTAS NOVAS E CORRETAS
app.include_router(imovel_router, prefix="/api", tags=["Imóveis"])
app.include_router(matricula_router, prefix="/api", tags=["Matrículas"])

app.include_router(document_router, prefix="/api", tags=["Documents"])
app.include_router(documento_tecnico_router, prefix="/api", tags=["Documentos Técnicos"])
app.include_router(documento_tecnico_checklist_router, prefix="/api", tags=["Checklist Técnico"])

app.include_router(geometria_router, prefix="/api", tags=["Geometrias"])
app.include_router(sobreposicao_router, prefix="/api", tags=["Sobreposição"])
app.include_router(memorial_router, prefix="/api", tags=["Memorial"])
app.include_router(croqui_router, prefix="/api", tags=["Croqui"])

app.include_router(map_router, prefix="/api", tags=["Map"])

app.include_router(cartorio_router, prefix="/api", tags=["Cartórios"])
app.include_router(municipio_router, prefix="/api", tags=["Municípios"])
app.include_router(confrontante_router, prefix="/api", tags=["Confrontantes"])

app.include_router(timeline_router, prefix="/api", tags=["Timeline"])
app.include_router(upload_router, prefix="/api", tags=["Uploads"])
app.include_router(files_routes.router, prefix="/api", tags=["Arquivos"])

app.include_router(calculation_router, prefix="/api", tags=["Cálculo"])
app.include_router(calculation_parameter_router, prefix="/api", tags=["Parâmetros"])

app.include_router(proposal_router, prefix="/api", tags=["Propostas"])
app.include_router(pagamento_router, prefix="/api", tags=["Pagamentos"])

app.include_router(checkout_router, prefix="/api", tags=["Pagamentos"])
app.include_router(webhook_router, prefix="/api", tags=["Pagamentos Webhook"])


app.include_router(profissional_router, prefix="/api", tags=["Profissionais"])
app.include_router(proposta_profissional_router, prefix="/api", tags=["Propostas Profissionais"])
app.include_router(projeto_profissional_router, prefix="/api", tags=["Projeto ⇄ Profissional"])
app.include_router(profissional_selecao_router, prefix="/api", tags=["Seleção Profissional"])
app.include_router(profissional_avaliacao_router, prefix="/api", tags=["Avaliação Profissional"])
app.include_router(profissional_ranking_router, prefix="/api", tags=["Ranking Profissional"])

app.include_router(requerimentos_router, prefix="/api", tags=["Requerimentos"])
app.include_router(sigef_export_router, prefix="/api", tags=["SIGEF"])
app.include_router(audit_log_router, prefix="/api", tags=["Audit Logs"])

app.include_router(template_router, prefix="/api", tags=["Templates"])



# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "GeoINCRA Backend",
        "docs": "/docs",
    }
