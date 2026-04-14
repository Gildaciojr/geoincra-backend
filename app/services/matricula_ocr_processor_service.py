from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.matricula import Matricula
from app.models.confrontante import Confrontante
from app.models.ocr_result import OcrResult

from app.services.ocr_normalizer import normalizar_dados_ocr
from app.services.memorial_parser_service import MemorialParserService
from app.services.memorial_service import MemorialService
from app.services.geometria_service import GeometriaService
from app.services.geometria_persistencia_service import GeometriaPersistenciaService


class MatriculaOcrProcessorService:

    @staticmethod
    def _normalizar_matricula(valor: Any) -> str | None:
        if not valor:
            return None

        texto = str(valor).strip()
        texto = re.sub(r"[^\d./-]", "", texto)

        return texto or None

    @staticmethod
    def _normalizar_nome(valor: Any) -> str | None:
        if not valor:
            return None
        return " ".join(str(valor).strip().split())

    @staticmethod
    def processar_documento(db: Session, document_id: int) -> Dict[str, Any]:

        try:

            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise Exception("Documento não encontrado.")

            ocr = (
                db.query(OcrResult)
                .filter(OcrResult.document_id == document_id)
                .order_by(OcrResult.created_at.desc())
                .first()
            )

            if not ocr:
                raise Exception("Resultado OCR não encontrado.")

            if not ocr.dados_extraidos_json:
                raise Exception("OCR não possui dados estruturados.")

            dados_brutos = MatriculaOcrProcessorService._parse_json(
                ocr.dados_extraidos_json
            )

            try:
                dados = normalizar_dados_ocr(dados_brutos)
            except Exception as e:
                raise Exception(f"OCR inválido após normalização: {str(e)}")

            numero_matricula = MatriculaOcrProcessorService._normalizar_matricula(
                dados.get("numero_matricula")
                or (dados.get("matricula") or {}).get("numero")
                or dados.get("matricula")
            )

            if not numero_matricula:
                raise Exception("Número da matrícula não encontrado no OCR.")

            # =========================================================
            # MATRÍCULA
            # =========================================================

            matricula = (
                db.query(Matricula)
                .filter(Matricula.numero_matricula == numero_matricula)
                .first()
            )

            if not matricula:

                matricula = Matricula(
                    numero_matricula=numero_matricula,
                    livro=dados.get("livro"),
                    folha=dados.get("folha"),
                    comarca=dados.get("comarca"),
                    codigo_cartorio=dados.get("codigo_cartorio"),
                    inteiro_teor=ocr.texto_extraido,
                    arquivo_path=document.file_path,
                    observacoes="Criado automaticamente via OCR"
                )

                db.add(matricula)
                db.flush()

            else:

                matricula.livro = dados.get("livro") or matricula.livro
                matricula.folha = dados.get("folha") or matricula.folha
                matricula.comarca = dados.get("comarca") or matricula.comarca
                matricula.codigo_cartorio = (
                    dados.get("codigo_cartorio")
                    or matricula.codigo_cartorio
                )

                matricula.inteiro_teor = (
                    ocr.texto_extraido
                    or matricula.inteiro_teor
                )

                if document.file_path:
                    matricula.arquivo_path = document.file_path

            # =========================================================
            # PROPRIETÁRIOS (NORMALIZADOS)
            # =========================================================

            proprietarios = dados.get("proprietarios")

            if proprietarios and isinstance(proprietarios, list):

                proprietarios_validos = []

                for p in proprietarios:

                    if not isinstance(p, dict):
                        continue

                    nome = MatriculaOcrProcessorService._normalizar_nome(p.get("nome"))
                    cpf_cnpj = p.get("cpf_cnpj")
                    tipo = p.get("tipo")

                    if not nome:
                        continue

                    proprietarios_validos.append(
                        {
                            "nome": nome,
                            "cpf_cnpj": cpf_cnpj,
                            "tipo": tipo,
                        }
                    )

                # Mantemos os proprietários estruturados no payload normalizado,
                # sem poluir o inteiro_teor da matrícula com dados derivados do OCR.
                proprietarios = proprietarios_validos

            # =========================================================
            # CONFRONTANTES (MELHORADO)
            # =========================================================

            confrontantes = dados.get("confrontantes")

            if confrontantes and isinstance(confrontantes, list):
                MatriculaOcrProcessorService._salvar_confrontantes(
                    db=db,
                    matricula=matricula,
                    confrontantes=confrontantes
                )

            # =========================================================
            # MEMORIAL → GEOMETRIA
            # =========================================================

            geojson = None
            geometria_payload = dados.get("geometria") or {}

            if not isinstance(geometria_payload, dict):
                geometria_payload = {}

            memorial_texto = (
                geometria_payload.get("memorial_texto")
                or dados.get("memorial_texto")
            )

            geojson = geometria_payload.get("geojson")

            # =========================================================
            # 🔥 TENTATIVA DE GERAR GEOJSON VIA PARSER
            # =========================================================
            if not geojson and memorial_texto:
                try:
                    parsed = MemorialParserService.gerar_geometria(memorial_texto)
                    geojson = parsed.get("geojson")
                except Exception as e:
                    print(f"[ERRO] Parser de memorial falhou: {str(e)}")
                    geojson = None

            # =========================================================
            # 🔥 PIPELINE DE GEOMETRIA COMPLETO
            # =========================================================
            if geojson:

                try:
                    # =========================================================
                    # SALVAR GEOMETRIA BASE
                    # =========================================================
                    geometria = GeometriaService.salvar_geometria(
                        db=db,
                        imovel_id=matricula.imovel_id,
                        geojson=geojson
                    )

                    # =========================================================
                    # 🔥 PERSISTÊNCIA DE ENGENHARIA (VÉRTICES + SEGMENTOS)
                    # =========================================================
                    try:
                        GeometriaPersistenciaService.persistir_estrutura(
                            db=db,
                            geometria_id=geometria.id,
                            geojson=geojson
                        )
                    except Exception as e:
                        print(f"[ERRO] Persistência de geometria falhou: {str(e)}")

                    # =========================================================
                    # 🔥 GERAÇÃO DO MEMORIAL TÉCNICO
                    # =========================================================
                    try:
                        MemorialService.gerar_memorial(
                            geometria_id=geometria.id,
                            geojson=geojson,
                            area_hectares=dados.get("area_hectares") or dados.get("area_total") or 0,
                            perimetro_m=getattr(geometria, "perimetro_m", 0) or 0,
                            imovel_id=matricula.imovel_id
                        )
                    except Exception as e:
                        print(f"[ERRO] Geração de memorial falhou: {str(e)}")

                except Exception as e:
                    print(f"[ERRO] Falha ao salvar geometria: {str(e)}")
                    geojson = None

            # =========================================================
            # COMMIT FINAL
            # =========================================================
            db.commit()
            db.refresh(matricula)

            return {
                "status": "SUCCESS",
                "matricula_id": matricula.id,
                "geojson": geojson
            }

        except Exception as e:

            db.rollback()

            return {
                "status": "ERROR",
                "message": str(e)
            }

    @staticmethod
    def _salvar_confrontantes(
        db: Session,
        matricula: Matricula,
        confrontantes: List[Dict[str, Any]]
    ):

        imovel_id = matricula.imovel_id

        if not imovel_id:
            return

        for item in confrontantes:

            if not isinstance(item, dict):
                continue

            # =========================================================
            # 🔥 DIREÇÃO (PRIORIDADE CORRETA DO NORMALIZADOR)
            # =========================================================
            direcao = (
                item.get("direcao")  # já vem pronto do normalizador
                or item.get("lado_normalizado")
                or item.get("lado")
            )

            # fallback defensivo
            if isinstance(direcao, str):
                direcao = direcao.strip().upper()

            if not direcao:
                direcao = "NAO_INFORMADO"

            # =========================================================
            # CAMPOS PRINCIPAIS
            # =========================================================
            nome = item.get("nome") or item.get("descricao")
            matricula_cft = item.get("matricula")
            identificacao = item.get("identificacao")
            descricao = item.get("descricao")

            # normalização leve (sem alterar estrutura original)
            if isinstance(nome, str):
                nome = nome.strip()

            if isinstance(identificacao, str):
                identificacao = identificacao.strip()

            if isinstance(descricao, str):
                descricao = descricao.strip()

            if isinstance(matricula_cft, str):
                matricula_cft = matricula_cft.strip()

            # =========================================================
            # VALIDAÇÃO DE CONTEÚDO
            # =========================================================
            if not any([nome, matricula_cft, identificacao, descricao]):
                continue

            # =========================================================
            # 🔥 DEDUPLICAÇÃO MAIS ROBUSTA
            # =========================================================
            existente = (
                db.query(Confrontante)
                .filter(
                    Confrontante.imovel_id == imovel_id,
                    Confrontante.direcao == direcao,
                    Confrontante.nome_confrontante == nome,
                    Confrontante.identificacao_imovel_confrontante == identificacao,
                )
                .first()
            )

            if existente:
                continue

            # =========================================================
            # INSERT
            # =========================================================
            db.add(
                Confrontante(
                    imovel_id=imovel_id,
                    direcao=direcao,
                    nome_confrontante=nome,
                    matricula_confrontante=matricula_cft,
                    identificacao_imovel_confrontante=identificacao,
                    descricao=descricao,
                )
            )

    @staticmethod
    def _parse_json(raw: Any) -> Dict[str, Any]:

        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):

            raw = raw.strip()

            try:
                return json.loads(raw)

            except Exception:
                return {"raw_result": raw}

        return {}

    @staticmethod
    def gerar_payload_documentos(
        db: Session,
        matricula_id: int
    ) -> Dict[str, Any]:

        matricula = (
            db.query(Matricula)
            .filter(Matricula.id == matricula_id)
            .first()
        )

        if not matricula:
            raise Exception("Matrícula não encontrada.")

        confrontantes = (
            db.query(Confrontante)
            .filter(Confrontante.imovel_id == matricula.imovel_id)
            .all()
        )

        # =========================================================
        # 🔥 OCR VINCULADO AO DOCUMENTO CORRETO
        # =========================================================

        ocr = (
            db.query(OcrResult)
            .join(Document, Document.id == OcrResult.document_id)
            .filter(Document.file_path == matricula.arquivo_path)
            .order_by(OcrResult.created_at.desc())
            .first()
        )

        dados_ocr = {}
        dados_normalizados = {}

        if ocr and ocr.dados_extraidos_json:
            dados_ocr = MatriculaOcrProcessorService._parse_json(
                ocr.dados_extraidos_json
            )

            try:
                from app.services.ocr_normalizer import normalizar_dados_ocr
                dados_normalizados = normalizar_dados_ocr(dados_ocr)
            except Exception:
                dados_normalizados = {}

        # =========================================================
        # 🔥 PROPRIETÁRIOS (NORMALIZADOS)
        # =========================================================

        proprietarios = []

        if isinstance(dados_normalizados.get("proprietarios"), list):
            for p in dados_normalizados.get("proprietarios"):

                if not isinstance(p, dict):
                    continue

                nome = p.get("nome")
                cpf = p.get("cpf_cnpj")
                tipo = p.get("tipo")

                if not nome:
                    continue

                proprietarios.append({
                    "nome": nome,
                    "cpf_cnpj": cpf,
                    "tipo": tipo,
                })

        # =========================================================
        # 🔥 DADOS NORMALIZADOS DO IMÓVEL
        # =========================================================

        descricao_imovel = dados_normalizados.get("descricao_imovel")
        area_total = dados_normalizados.get("area_total")
        unidade_area = dados_normalizados.get("unidade_area")
        area_hectares = dados_normalizados.get("area_hectares")

        # =========================================================
        # 🔥 NORMALIZAÇÃO LEVE (SEM QUEBRAR NADA)
        # =========================================================

        def _safe(v):
            if v is None:
                return None
            return str(v).strip()

        # =========================================================
        # PAYLOAD FINAL (EXPANDIDO E CONSISTENTE)
        # =========================================================

        return {
            # 🔹 LEGADO (NÃO ALTERAR)
            "matricula": matricula.numero_matricula,
            "livro": matricula.livro,
            "folha": matricula.folha,
            "comarca": matricula.comarca,
            "codigo_cartorio": matricula.codigo_cartorio,
            "status": matricula.status,

            # 🔥 CAMPOS PADRONIZADOS
            "numero_matricula": matricula.numero_matricula,
            "descricao_imovel": _safe(descricao_imovel),
            "area_total": area_total,
            "unidade_area": unidade_area,
            "area_hectares": area_hectares,

            "proprietarios": proprietarios,

            "confrontantes": [
                {
                    "direcao": c.direcao,
                    "nome": c.nome_confrontante,
                    "matricula": c.matricula_confrontante,
                    "descricao": c.descricao,
                    "identificacao": c.identificacao_imovel_confrontante,
                }
                for c in confrontantes
            ],

            # 🔥 DEBUG / RASTREABILIDADE
            "metadata": {
                "origem": "matricula_ocr_processor_service",
                "possui_ocr": bool(dados_normalizados),
                "total_confrontantes": len(confrontantes),
                "total_proprietarios": len(proprietarios),
                "normalizado": True,
            }
        }