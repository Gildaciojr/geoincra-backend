from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.automation_job_crud import create_ocr_job

from app.models.document import Document
from app.models.ocr_prompt import OcrPrompt
from app.models.ocr_result import OcrResult


class OcrService:

    # =========================================================
    # PROVIDERS SUPORTADOS
    # =========================================================
    PROVIDERS_SUPORTADOS = {
        "GOOGLE",
        "OPENAI",
        "AZURE",
        "AWS_TEXTRACT",
        "GEMINI",
    }

    # =========================================================
    # CATEGORIAS OCR SUPORTADAS
    # =========================================================
    CATEGORIAS_SUPORTADAS = {

        # =====================================================
        # MATRÍCULA
        # =====================================================
        "MATRICULA",
        "MATRICULA_IMOVEL",
        "ANALISE_MATRICULA",
        "ANALISE_MATRICULA_COMPLETA",
        "ANALISE_DE_MATRICULA_DE_IMOVEL",
        "ANALISE_TECNICA_COMPLETA_DE_MATRICULA",

        # =====================================================
        # DOCUMENTO PESSOAL
        # =====================================================
        "DOCUMENTO_PESSOAL",
        "DOCUMENTOS_PESSOAIS",
        "EXTRACAO_DOCUMENTOS_PESSOAIS",
        "EXTRACAO_DE_DOCUMENTOS_PESSOAIS",
        "RG_CPF_CNH",

        # =====================================================
        # FICHA SIG
        # =====================================================
        "FICHA_CADASTRAL_SIG",
        "FICHA_IMOVEL_SIG",
        "FICHA_CADASTRAL_DE_IMOVEL_SIG",
        "FICHA_CADASTRAL_IMOVEL_SIG",
        "SIG",
        "CADASTRO_SIG",
        "CADASTRO_IMOVEL_SIG"

        # =====================================================
        # CONFRONTANTES
        # =====================================================
        "CONFRONTANTES_CROQUI",
        "INSERCAO_CONFRONTANTES_CROQUI",
        "INSERCAO_DE_CONFRONTANTES_NO_CROQUI",
        "INSERIR_CONFRONTANTES_NO_CROQUI",
        "CROQUI_CONFRONTANTES",

        # =====================================================
        # DADOS BRUTOS
        # =====================================================
        "DADOS_BRUTOS",
        "DADOS_BRUTOS_COMPLETO",
        "DADOS_BRUTOS_DE_DOCUMENTOS",
        "DADOS_BRUTOS_DO_DOCUMENTO",
        "EXTRACAO_DADOS_BRUTOS",
        "EXTRACAO_BRUTA",

        # =====================================================
        # MEMORIAL DESCRITIVO
        # =====================================================
        "MEMORIAL_DESCRITIVO",
    }

    # =========================================================
    # INICIAR OCR
    # =========================================================
    @staticmethod
    def iniciar_ocr(
        db: Session,
        document_id: int,
        user_id: int,
        prompt_id: int,
        provider: str = "GOOGLE",
    ) -> OcrResult:

        # =====================================================
        # DOCUMENTO
        # =====================================================
        doc = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not doc:
            raise HTTPException(
                status_code=404,
                detail="Documento não encontrado.",
            )

        # =====================================================
        # PROMPT OCR
        # =====================================================
        prompt = (
            db.query(OcrPrompt)
            .filter(
                OcrPrompt.id == prompt_id,
                OcrPrompt.ativo == True,
            )
            .first()
        )

        if not prompt:
            raise HTTPException(
                status_code=404,
                detail="Prompt OCR não encontrado.",
            )

        # =====================================================
        # PROVIDER
        # =====================================================
        provider_normalizado = (
            str(provider)
            .strip()
            .upper()
        )

        if (
            provider_normalizado
            not in OcrService.PROVIDERS_SUPORTADOS
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Provider OCR inválido: "
                    f"{provider_normalizado}"
                ),
            )

        # =====================================================
        # CATEGORIA
        # =====================================================
        categoria_prompt = (
            str(prompt.categoria or "")
            .strip()
            .upper()
        )

        if (
            categoria_prompt
            not in OcrService.CATEGORIAS_SUPORTADAS
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Categoria OCR não suportada: "
                    f"{categoria_prompt}"
                ),
            )

        # =====================================================
        # OCR EXISTENTE EM PROCESSAMENTO
        # =====================================================
        ocr_em_execucao = (
            db.query(OcrResult)
            .filter(
                OcrResult.document_id == document_id,
                OcrResult.status.in_(
                    [
                        "PENDING",
                        "PROCESSING",
                    ]
                ),
            )
            .order_by(OcrResult.created_at.desc())
            .first()
        )

        if ocr_em_execucao:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Já existe OCR em processamento "
                    "para este documento."
                ),
            )

        # =====================================================
        # REGISTRO OCR
        # =====================================================
        ocr = OcrResult(
            document_id=document_id,

            # =================================================
            # STATUS
            # =================================================
            status="PENDING",

            # =================================================
            # ENGINE / PROVIDER
            # =================================================
            provider=provider_normalizado,

            engine_version=(
                provider_normalizado
            ),

            modelo_llm=(
                prompt.modelo_llm
                if hasattr(
                    prompt,
                    "modelo_llm",
                )
                else None
            ),

            # =================================================
            # PROMPT
            # =================================================
            ocr_prompt_id=prompt.id,

            prompt_nome=prompt.nome,

            prompt_slug=(
                prompt.slug
                if hasattr(
                    prompt,
                    "slug",
                )
                else None
            ),

            # =================================================
            # PIPELINE
            # =================================================
            pipeline_tipo=(
                prompt.pipeline
                if hasattr(
                    prompt,
                    "pipeline",
                )
                and prompt.pipeline
                else categoria_prompt
            ),

            pipeline_versao=(
                f"OCR_PIPELINE_V"
                f"{prompt.versao}"
                if hasattr(
                    prompt,
                    "versao",
                )
                and prompt.versao
                else "OCR_PIPELINE_V2"
            ),

            # =================================================
            # PARSER / NORMALIZER
            # =================================================
            parser_utilizado=(
                OcrService
                .resolver_parser_por_categoria(
                    categoria_prompt
                )
            ),

            normalizador_utilizado=(
                OcrService
                .resolver_normalizador_por_categoria(
                    categoria_prompt
                )
            ),

            parser_version="1.0.0",

            normalizer_version="1.0.0",

            schema_version="1.0.0",

            # =================================================
            # OCR / PROCESSAMENTO
            # =================================================
            total_paginas=None,

            paginas_processadas=None,

            score_confianca=None,

            score_extracao=None,

            score_geometria=None,

            score_registral=None,

            processado_em=None,

            started_at=None,

            finished_at=None,

            # =================================================
            # FLAGS
            # =================================================
            possui_geojson=0,

            possui_memorial=0,

            possui_confrontantes=0,

            possui_historico=0,

            possui_documentos_pessoais=(
                1
                if categoria_prompt
                == "DOCUMENTO_PESSOAL"
                else 0
            ),

            possui_dados_sigef=(
                1
                if categoria_prompt
                == "FICHA_CADASTRAL_SIG"
                else 0
            ),

            possui_croqui=(
                1
                if categoria_prompt
                == "CONFRONTANTES_CROQUI"
                else 0
            ),

            # =================================================
            # METADATA
            # =================================================
            metadata_json={
                "prompt_id": prompt.id,

                "prompt_nome": prompt.nome,

                "prompt_slug": (
                    prompt.slug
                    if hasattr(
                        prompt,
                        "slug",
                    )
                    else None
                ),

                "categoria": categoria_prompt,

                "pipeline": (
                    prompt.pipeline
                    if hasattr(
                        prompt,
                        "pipeline",
                    )
                    else None
                ),

                "provider": (
                    provider_normalizado
                ),

                "modelo_llm": (
                    prompt.modelo_llm
                    if hasattr(
                        prompt,
                        "modelo_llm",
                    )
                    else None
                ),

                "parser_utilizado": (
                    OcrService
                    .resolver_parser_por_categoria(
                        categoria_prompt
                    )
                ),

                "normalizador_utilizado": (
                    OcrService
                    .resolver_normalizador_por_categoria(
                        categoria_prompt
                    )
                ),

                "pipeline_versao": (
                    f"OCR_PIPELINE_V"
                    f"{prompt.versao}"
                    if hasattr(
                        prompt,
                        "versao",
                    )
                    and prompt.versao
                    else "OCR_PIPELINE_V2"
                ),
            },

            warnings_json=[],

            errors_json=[],
        )

        db.add(ocr)

        db.commit()
        db.refresh(ocr)

        # =====================================================
        # JOB OCR
        # =====================================================
        create_ocr_job(
            db=db,

            user_id=user_id,

            project_id=doc.project_id,

            document_id=document_id,

            prompt_id=prompt_id,

            ocr_result_id=ocr.id,
        )

        return ocr

    # =========================================================
    # RESOLVER PARSER OCR
    # =========================================================
    @staticmethod
    def resolver_parser_por_categoria(
        categoria: str,
    ) -> Optional[str]:

        categoria_upper = (
            str(categoria or "")
            .strip()
            .upper()
        )

        mapping = {
            "MATRICULA":
                "MatriculaOCRParser",

            "DOCUMENTO_PESSOAL":
                "DocumentoPessoalOCRParser",

            "FICHA_CADASTRAL_SIG":
                "FichaCadastralSIGParser",

            "CONFRONTANTES_CROQUI":
                "ConfrontantesCroquiParser",

            "DADOS_BRUTOS":
                "RawDocumentOCRParser",

            "MEMORIAL_DESCRITIVO":
                "MemorialOCRParser",
        }

        return mapping.get(categoria_upper)

    # =========================================================
    # RESOLVER NORMALIZADOR
    # =========================================================
    @staticmethod
    def resolver_normalizador_por_categoria(
        categoria: str,
    ) -> Optional[str]:

        categoria_upper = (
            str(categoria or "")
            .strip()
            .upper()
        )

        mapping = {
            "MATRICULA":
                "normalizar_dados_ocr",

            "DOCUMENTO_PESSOAL":
                "normalizar_documento_pessoal",

            "FICHA_CADASTRAL_SIG":
                "normalizar_ficha_sig",

            "CONFRONTANTES_CROQUI":
                "normalizar_confrontantes_croqui",

            "DADOS_BRUTOS":
                "normalizar_documento_bruto",

            "MEMORIAL_DESCRITIVO":
                "normalizar_memorial_ocr",
        }

        return mapping.get(categoria_upper)