from __future__ import annotations

import json
import re
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.models.confrontante import Confrontante
from app.models.ocr_result import OcrResult
from app.models.proprietario import Proprietario

from app.services.ocr_normalizer import normalizar_dados_ocr
from app.services.memorial_parser_service import MemorialParserService
from app.services.memorial_service import MemorialService
from app.services.geometria_service import GeometriaService
from app.services.geometria_persistencia_service import GeometriaPersistenciaService

logger = logging.getLogger(__name__)


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
    def _normalizar_cpf_cnpj(valor: Any) -> str | None:
        if not valor:
            return None

        texto = re.sub(r"\D", "", str(valor))

        if len(texto) == 11:
            return f"{texto[:3]}.{texto[3:6]}.{texto[6:9]}-{texto[9:]}"
        if len(texto) == 14:
            return f"{texto[:2]}.{texto[2:5]}.{texto[5:8]}/{texto[8:12]}-{texto[12:]}"

        valor_str = str(valor).strip()
        return valor_str or None

    @staticmethod
    def _normalizar_tipo_pessoa(valor: Any, cpf_cnpj: Any = None) -> str:
        texto = str(valor or "").strip().upper()

        if texto in {"FISICA", "FÍSICA", "PF"}:
            return "FISICA"

        if texto in {"JURIDICA", "JURÍDICA", "PJ"}:
            return "JURIDICA"

        numeros = re.sub(r"\D", "", str(cpf_cnpj or ""))

        if len(numeros) == 14:
            return "JURIDICA"

        return "FISICA"

    @staticmethod
    def _resolver_imovel_principal(db: Session, document: Document) -> Imovel:
        imovel = (
            db.query(Imovel)
            .filter(Imovel.project_id == document.project_id)
            .order_by(Imovel.id.asc())
            .first()
        )

        if not imovel:
            raise Exception(
                "Projeto do documento não possui imóvel cadastrado para vincular a matrícula OCR."
            )

        return imovel

    @staticmethod
    def _upsert_matricula_principal(
        db: Session,
        *,
        imovel: Imovel,
        document: Document,
        ocr: OcrResult,
        dados: Dict[str, Any],
        numero_matricula: str,
    ) -> Matricula:
        # =========================================================
        # 🔥 RESOLVE CARTÓRIO (OCR → DB)
        # =========================================================
        cartorio_id = MatriculaOcrProcessorService._resolver_cartorio(
            db,
            dados,
        )

        matricula = (
            db.query(Matricula)
            .filter(
                Matricula.imovel_id == imovel.id,
                Matricula.numero_matricula == numero_matricula,
            )
            .first()
        )

        # =========================================================
        # CREATE
        # =========================================================
        if not matricula:
            matricula = Matricula(
                imovel_id=imovel.id,
                numero_matricula=numero_matricula,
                livro=dados.get("livro"),
                folha=dados.get("folha"),
                comarca=dados.get("comarca"),
                codigo_cartorio=dados.get("codigo_cartorio"),

                # 🔥 NOVO (INTEGRAÇÃO DIRETA)
                cartorio_id=cartorio_id if cartorio_id else None,

                inteiro_teor=ocr.texto_extraido,
                arquivo_path=document.file_path,
                observacoes=(
                    "Criado automaticamente via OCR | "
                    f"ocr_result_id={ocr.id}"
                ),
            )

            db.add(matricula)
            db.flush()
            return matricula

        # =========================================================
        # UPDATE (MERGE INTELIGENTE)
        # =========================================================
        if dados.get("livro"):
            matricula.livro = dados.get("livro")

        if dados.get("folha"):
            matricula.folha = dados.get("folha")

        if dados.get("comarca"):
            matricula.comarca = dados.get("comarca")

        if dados.get("codigo_cartorio"):
            matricula.codigo_cartorio = dados.get("codigo_cartorio")

        # 🔥 NOVO — atualiza cartório apenas se ainda não existir
        if not matricula.cartorio_id and cartorio_id:
            matricula.cartorio_id = cartorio_id

        if ocr.texto_extraido:
            matricula.inteiro_teor = ocr.texto_extraido

        observacao_atual = (
            matricula.observacoes or ""
        )

        rastreamento = (
             f"ocr_result_id={ocr.id}"
        )

        if rastreamento not in observacao_atual:
            matricula.observacoes = (
                f"{observacao_atual} | {rastreamento}"
                if observacao_atual
                else rastreamento
            )


        if document.file_path:
            matricula.arquivo_path = document.file_path

        return matricula
    
    @staticmethod
    def _normalizar_proprietarios_ocr(
        proprietarios: Any,
    ) -> List[Dict[str, Any]]:
        proprietarios_validos: List[Dict[str, Any]] = []
        chaves_vistas: set[tuple[str, str, str]] = set()

        if not proprietarios or not isinstance(proprietarios, list):
            return proprietarios_validos

        for p in proprietarios:
            if not isinstance(p, dict):
                continue

            nome = MatriculaOcrProcessorService._normalizar_nome(p.get("nome"))
            cpf_cnpj = MatriculaOcrProcessorService._normalizar_cpf_cnpj(
                p.get("cpf_cnpj")
            )
            tipo = MatriculaOcrProcessorService._normalizar_tipo_pessoa(
                p.get("tipo"),
                cpf_cnpj=cpf_cnpj,
            )

            if not nome:
                continue

            chave = (
                nome.upper(),
                re.sub(r"\D", "", str(cpf_cnpj or "")),
                tipo,
            )

            if chave in chaves_vistas:
                continue

            chaves_vistas.add(chave)

            proprietarios_validos.append(
                {
                    "nome": nome,
                    "cpf_cnpj": cpf_cnpj,
                    "tipo": tipo,
                }
            )

        return proprietarios_validos

    @staticmethod
    def _resolver_cartorio(
        db: Session,
        dados: Dict[str, Any]
    ) -> Optional[int]:
        from app.models.cartorio import Cartorio

        nome = (
            (dados.get("matricula") or {}).get("cartorio")
            or dados.get("cartorio")
        )

        comarca = dados.get("comarca")

        if not nome:
            return None

        nome = str(nome).strip().upper()

        existente = (
            db.query(Cartorio)
            .filter(Cartorio.nome.ilike(f"%{nome}%"))
            .first()
        )

        if existente:
            return existente.id

        novo = Cartorio(
            nome=nome,
            comarca=comarca,
            origem="OCR",
        )

        db.add(novo)
        db.flush()

        return novo.id

    @staticmethod
    def _persistir_proprietarios(
        db: Session,
        *,
        imovel: Imovel,
        matricula: Matricula,
        proprietarios: List[Dict[str, Any]],
    ) -> None:
        if not proprietarios:
            return

        def _somente_digitos(v: Any) -> str:
            return re.sub(r"\D", "", str(v or ""))

        for p in proprietarios:
            nome = MatriculaOcrProcessorService._normalizar_nome(p.get("nome"))

            cpf_cnpj = MatriculaOcrProcessorService._normalizar_cpf_cnpj(
                p.get("cpf_cnpj")
            )

            tipo = MatriculaOcrProcessorService._normalizar_tipo_pessoa(
                p.get("tipo"),
                cpf_cnpj=cpf_cnpj,
            )

            if not nome:
                continue

            cpf = None
            cnpj = None

            numeros = _somente_digitos(cpf_cnpj)

            if len(numeros) == 11:
                cpf = cpf_cnpj
            elif len(numeros) == 14:
                cnpj = cpf_cnpj

            # =========================================================
            # ESTRATÉGIA DE MATCH PROFISSIONAL
            # =========================================================
            existente = None

            # 1. CPF (mais forte)
            if cpf:
                existente = (
                    db.query(Proprietario)
                    .filter(Proprietario.cpf == cpf)
                    .first()
                )

            # 2. CNPJ
            if not existente and cnpj:
                existente = (
                    db.query(Proprietario)
                    .filter(Proprietario.cnpj == cnpj)
                    .first()
                )

            # 3. Nome + imóvel (fallback)
            if not existente:
                existente = (
                    db.query(Proprietario)
                    .filter(
                        Proprietario.imovel_id == imovel.id,
                        Proprietario.nome_completo == nome,
                    )
                    .first()
                )

            # =========================================================
            # UPDATE (MERGE INTELIGENTE)
            # =========================================================
            if existente:
                if not existente.matricula_id:
                    existente.matricula_id = matricula.id

                if cpf and not existente.cpf:
                    existente.cpf = cpf

                if cnpj and not existente.cnpj:
                    existente.cnpj = cnpj

                existente.tipo_pessoa = tipo or existente.tipo_pessoa

                if not existente.origem:
                    existente.origem = "OCR"

                if not existente.observacoes:
                    existente.observacoes = "Atualizado automaticamente via OCR da matrícula"

                continue

            # =========================================================
            # INSERT COMPLETO
            # =========================================================
            db.add(
                Proprietario(
                    imovel_id=imovel.id,
                    matricula_id=matricula.id,
                    nome_completo=nome,
                    tipo_pessoa=tipo,
                    cpf=cpf,
                    cnpj=cnpj,
                    origem="OCR",
                    observacoes="Criado automaticamente via OCR da matrícula",
                )
            )

    @staticmethod
    def _salvar_confrontantes(
        db: Session,
        matricula: Matricula,
        confrontantes: List[Dict[str, Any]]
    ):

        imovel_id = matricula.imovel_id

        if not imovel_id:
            return

        def _limpar_texto(valor: Any) -> str | None:
            if not valor:
                return None
            texto = str(valor).strip()
            texto = " ".join(texto.split())
            return texto or None

        def _normalizar_matricula(valor: Any) -> str | None:
            if not valor:
                return None
            texto = re.sub(r"[^\d./-]", "", str(valor))
            return texto or None

        def _is_texto_institucional(texto: str | None) -> bool:
            if not texto:
                return False

            texto_upper = texto.upper()

            palavras_ruins = [
                "CARTORIO",
                "CARTÓRIO",
                "REGISTRO DE IMOVEIS",
                "REGISTRO DE IMÓVEIS",
                "OFICIO",
                "OFÍCIO",
                "COMARCA",
            ]

            return any(p in texto_upper for p in palavras_ruins)

        def _merge_texto(atual: Any, novo: Any) -> str | None:
            atual_limpo = _limpar_texto(atual)
            novo_limpo = _limpar_texto(novo)

            if atual_limpo and novo_limpo:
                return novo_limpo if len(novo_limpo) > len(atual_limpo) else atual_limpo

            return novo_limpo or atual_limpo

        for item in confrontantes:

            if not isinstance(item, dict):
                continue

            # =========================================================
            # DIREÇÃO
            # =========================================================
            direcao = (
                item.get("direcao")
                or item.get("lado_normalizado")
                or item.get("lado")
            )

            if isinstance(direcao, str):
                direcao = direcao.strip().upper()

            if not direcao:
                direcao = "NAO_INFORMADO"

            direcao_normalizada = (
                item.get("direcao_normalizada")
                or item.get("lado_normalizado")
            )

            if isinstance(direcao_normalizada, str):
                direcao_normalizada = direcao_normalizada.strip().upper()

            # =========================================================
            # CAMPOS
            # =========================================================
            nome = _limpar_texto(item.get("nome") or item.get("descricao"))
            identificacao = _limpar_texto(item.get("identificacao"))
            descricao = _limpar_texto(item.get("descricao"))
            matricula_cft = _normalizar_matricula(item.get("matricula"))

            tipo = _limpar_texto(item.get("tipo"))
            lote = _limpar_texto(item.get("lote"))
            gleba = _limpar_texto(item.get("gleba"))

            # =========================================================
            # SANITIZAÇÃO
            # =========================================================
            if _is_texto_institucional(nome):
                nome = None

            if _is_texto_institucional(descricao):
                descricao = None

            # =========================================================
            # VALIDAÇÃO (AGORA CORRETA)
            # =========================================================
            if not any([nome, matricula_cft, identificacao, descricao, tipo, lote, gleba]):
                continue

            # =========================================================
            # DEDUPLICAÇÃO
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

            if not existente and matricula_cft:
                existente = (
                    db.query(Confrontante)
                    .filter(
                        Confrontante.imovel_id == imovel_id,
                        Confrontante.matricula_confrontante == matricula_cft,
                    )
                    .first()
                )

            if not existente:
                existente = (
                    db.query(Confrontante)
                    .filter(
                        Confrontante.imovel_id == imovel_id,
                        Confrontante.direcao == direcao,
                        Confrontante.descricao == descricao,
                    )
                    .first()
                )

            observacoes_partes = ["Atualizado automaticamente via OCR"]

            if tipo:
                observacoes_partes.append(f"TIPO={tipo}")
            if lote:
                observacoes_partes.append(f"LOTE={lote}")
            if gleba:
                observacoes_partes.append(f"GLEBA={gleba}")

            observacoes_texto = " | ".join(observacoes_partes)

            # =========================================================
            # UPDATE (AGORA COMPLETO)
            # =========================================================
            if existente:

                existente.matricula_id = existente.matricula_id or matricula.id
                existente.direcao = direcao
                existente.direcao_normalizada = (
                    direcao_normalizada or existente.direcao_normalizada
                )

                existente.nome_confrontante = _merge_texto(
                    existente.nome_confrontante, nome
                )
                existente.matricula_confrontante = _merge_texto(
                    existente.matricula_confrontante, matricula_cft
                )
                existente.identificacao_imovel_confrontante = _merge_texto(
                    existente.identificacao_imovel_confrontante,
                    identificacao,
                )
                existente.descricao = _merge_texto(
                    existente.descricao, descricao
                )

                existente.tipo = _merge_texto(existente.tipo, tipo)
                existente.lote = _merge_texto(existente.lote, lote)
                existente.gleba = _merge_texto(existente.gleba, gleba)

                existente.observacoes = _merge_texto(
                    existente.observacoes,
                    f"{observacoes_texto} | matricula_ref={matricula.numero_matricula}",
                )

                continue

            # =========================================================
            # INSERT (AGORA COMPLETO)
            # =========================================================
            db.add(
                Confrontante(
                    imovel_id=imovel_id,
                    geometria_id=None,
                    direcao=direcao,
                    direcao_normalizada=direcao_normalizada,
                    nome_confrontante=nome,
                    matricula_confrontante=matricula_cft,
                    matricula_id=matricula.id,
                    identificacao_imovel_confrontante=identificacao,
                    descricao=descricao,
                    tipo=tipo,
                    lote=lote,
                    gleba=gleba,
                    observacoes=f"{observacoes_texto} | matricula_ref={matricula.numero_matricula}",
                )
            )
    
    @staticmethod
    def processar_documento(db: Session, document_id: int) -> Dict[str, Any]:

        try:

            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise Exception("Documento não encontrado.")

            imovel = MatriculaOcrProcessorService._resolver_imovel_principal(
                db=db,
                document=document,
            )

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
            
            categoria_ocr = str(
                getattr(ocr, "categoria", "") or ""
            ).strip().upper()

            categorias_matricula_validas = {
                "MATRICULA",
                "ANALISE_MATRICULA",
                "ANALISE_MATRICULA_COMPLETA",
                "ANALISE_TECNICA_COMPLETA_MATRICULA",
            }

            if categoria_ocr not in categorias_matricula_validas:
                raise Exception(
                    "OCR incompatível com pipeline de matrícula."
                )

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
            # MATRÍCULA PRINCIPAL DO IMÓVEL OBJETO
            # =========================================================
            matricula = MatriculaOcrProcessorService._upsert_matricula_principal(
                db=db,
                imovel=imovel,
                document=document,
                ocr=ocr,
                dados=dados,
                numero_matricula=numero_matricula,
            )

            # =========================================================
            # PROPRIETÁRIOS (NORMALIZADOS + PERSISTIDOS)
            # =========================================================
            proprietarios = MatriculaOcrProcessorService._normalizar_proprietarios_ocr(
                dados.get("proprietarios")
            )

            if proprietarios:
                MatriculaOcrProcessorService._persistir_proprietarios(
                    db=db,
                    imovel=imovel,
                    matricula=matricula,
                    proprietarios=proprietarios,
                )

            # =========================================================
            # CONFRONTANTES (ESTRUTURA ATUAL + PREPARAÇÃO PARA EVOLUÇÃO)
            # =========================================================
            confrontantes = dados.get("confrontantes")

            confrontantes_normalizados = []

            if confrontantes and isinstance(confrontantes, list):
                for c in confrontantes:
                    if not isinstance(c, dict):
                        continue

                    direcao = (
                        c.get("direcao")
                        or c.get("lado")
                    )

                    direcao_normalizada = (
                        c.get("lado_normalizado")
                        or c.get("direcao_normalizada")
                    )

                    nome = c.get("nome")
                    descricao = c.get("descricao")
                    matricula_cft = c.get("matricula")
                    identificacao = c.get("identificacao")

                    # 🔥 validação mínima
                    if not any([nome, descricao, matricula_cft, identificacao]):
                        continue

                    confrontantes_normalizados.append(
                        {
                            "direcao": direcao,
                            "direcao_normalizada": direcao_normalizada,

                            "lado": direcao,
                            "lado_normalizado": direcao_normalizada,

                            "nome": nome,
                            "descricao": descricao,
                            "matricula": matricula_cft,
                            "identificacao": identificacao,

                            "tipo": c.get("tipo"),
                            "lote": c.get("lote"),
                            "gleba": c.get("gleba"),

                        }
                    )

            if confrontantes_normalizados:
                 MatriculaOcrProcessorService._salvar_confrontantes(
                    db=db,
                    matricula=matricula,
                    confrontantes=confrontantes_normalizados,
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
            # TENTATIVA DE GERAR GEOJSON VIA PARSER
            # =========================================================
            if not geojson and memorial_texto:
                try:
                    parsed = MemorialParserService.gerar_geometria(memorial_texto)
                    geojson = parsed.get("geojson")
                except Exception as e:
                    logger.exception(
                        "Parser de memorial OCR falhou."
                    )
                    geojson = None

            # =========================================================
            # PIPELINE DE GEOMETRIA COMPLETO
            # =========================================================
            geojson_normalizado = None

            if geojson:

                try:

                    geojson_normalizado = (
                        GeometriaService.validar_geojson(
                            geojson
                        )
                    )

                    if not geojson_normalizado:
                        raise Exception(
                            "GeoJSON inválido após validação."
                        )

                    geometria = (
                        GeometriaService.salvar_geometria(
                            db=db,
                            imovel_id=imovel.id,
                            geojson=geojson_normalizado,
                        )
                    )

                    try:

                        GeometriaPersistenciaService.persistir_estrutura(
                            db=db,
                            geometria_id=geometria.id,
                            geojson=geojson_normalizado,
                        )

                    except Exception as exc:

                        logger.exception(
                            "Persistência de geometria OCR falhou."
                        )

                    try:

                        MemorialService.gerar_memorial(
                            geometria_id=geometria.id,
                            geojson=geojson_normalizado,
                            area_hectares=(
                                dados.get("area_hectares")
                                or dados.get("area_total")
                                or 0
                            ),
                            perimetro_m=(
                                getattr(
                                    geometria,
                                    "perimetro_m",
                                    0,
                                )
                                or 0
                            ),
                            imovel_id=imovel.id,
                        )

                    except Exception as exc:

                        logger.exception(
                            "Geração de memorial OCR falhou."
                        )

                except Exception as exc:

                    logger.exception(
                        "Falha ao salvar geometria OCR."
                    )

                    geojson_normalizado = None

            # =========================================================
            # COMMIT FINAL
            # =========================================================
            db.commit()

            db.refresh(matricula)

            return {
                "status": "SUCCESS",
                "matricula_id": matricula.id,
                "imovel_id": imovel.id,
                "numero_matricula": (
                    matricula.numero_matricula
                ),
                "total_proprietarios": len(
                    proprietarios
                ),
                "geojson": geojson_normalizado,
            }

        except Exception as exc:

            db.rollback()

            return {
                "status": "ERROR",
                "message": str(exc),
            }


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

        if not matricula.imovel_id:
            raise Exception("Matrícula sem vínculo com imóvel.")

        imovel = (
            db.query(Imovel)
            .filter(Imovel.id == matricula.imovel_id)
            .first()
        )

        if not imovel:
            raise Exception("Imóvel vinculado à matrícula não encontrado.")

        confrontantes = (
            db.query(Confrontante)
            .filter(Confrontante.imovel_id == matricula.imovel_id)
            .order_by(Confrontante.id.asc())
            .all()
        )

        proprietarios_db = (
            db.query(Proprietario)
            .filter(Proprietario.imovel_id == matricula.imovel_id)
            .order_by(Proprietario.id.asc())
            .all()
        )

        # =========================================================
        # OCR VINCULADO AO DOCUMENTO CORRETO
        # =========================================================

        ocr = None

        if matricula.arquivo_path:
            ocr = (
                db.query(OcrResult)
                .join(Document, Document.id == OcrResult.document_id)
                .filter(Document.file_path == matricula.arquivo_path)
                .order_by(OcrResult.created_at.desc())
                .first()
            )

        dados_ocr: Dict[str, Any] = {}
        dados_normalizados: Dict[str, Any] = {}

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
        # NORMALIZAÇÃO LEVE / HELPERS
        # =========================================================

        def _safe(v: Any) -> Optional[str]:
            if v is None:
                return None
            texto = str(v).strip()
            return texto or None

        def _somente_digitos(v: Any) -> str:
            return re.sub(r"\D", "", str(v or ""))

        def _normalizar_cpf_cnpj(v: Any) -> Optional[str]:
            if not v:
                return None

            numeros = _somente_digitos(v)

            if len(numeros) == 11:
                return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
            if len(numeros) == 14:
                return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"

            texto = _safe(v)
            return texto

        def _normalizar_tipo_pessoa(valor: Any, cpf_cnpj: Any = None) -> str:
            texto = str(valor or "").strip().upper()

            if texto in {"FISICA", "FÍSICA", "PF"}:
                return "FISICA"

            if texto in {"JURIDICA", "JURÍDICA", "PJ"}:
                return "JURIDICA"

            numeros = _somente_digitos(cpf_cnpj)

            if len(numeros) == 14:
                return "JURIDICA"

            return "FISICA"

        # =========================================================
        # PROPRIETÁRIOS — FONTE OFICIAL: BANCO
        # =========================================================

        proprietarios: List[Dict[str, Any]] = []

        if proprietarios_db:
            for p in proprietarios_db:
                cpf_cnpj = p.cpf or p.cnpj

                proprietarios.append(
                    {
                        "nome": _safe(p.nome_completo),
                        "cpf_cnpj": _normalizar_cpf_cnpj(cpf_cnpj),
                        "tipo": _normalizar_tipo_pessoa(
                            p.tipo_pessoa,
                            cpf_cnpj=cpf_cnpj,
                        ),
                        "cpf": _normalizar_cpf_cnpj(p.cpf),
                        "cnpj": _normalizar_cpf_cnpj(p.cnpj),
                        "estado_civil": _safe(p.estado_civil),
                        "profissao": _safe(p.profissao),
                        "nacionalidade": _safe(p.nacionalidade),
                        "municipio": _safe(p.municipio),
                        "estado": _safe(p.estado),
                        "cep": _safe(p.cep),
                        "endereco": _safe(p.endereco),
                        "telefone": _safe(p.telefone),
                        "email": _safe(p.email),
                        "observacoes": _safe(p.observacoes),
                        "origem": "banco",
                    }
                )

        # fallback defensivo: se ainda não houver proprietários persistidos,
        # usa os normalizados do OCR sem quebrar o fluxo atual.
        if not proprietarios and isinstance(dados_normalizados.get("proprietarios"), list):
            for p in dados_normalizados.get("proprietarios"):
                if not isinstance(p, dict):
                    continue

                nome = _safe(p.get("nome"))
                cpf_cnpj = _normalizar_cpf_cnpj(p.get("cpf_cnpj"))
                tipo = _normalizar_tipo_pessoa(
                    p.get("tipo"),
                    cpf_cnpj=cpf_cnpj,
                )

                if not nome:
                    continue

                proprietarios.append(
                    {
                        "nome": nome,
                        "cpf_cnpj": cpf_cnpj,
                        "tipo": tipo,
                        "cpf": cpf_cnpj if len(_somente_digitos(cpf_cnpj)) == 11 else None,
                        "cnpj": cpf_cnpj if len(_somente_digitos(cpf_cnpj)) == 14 else None,
                        "estado_civil": None,
                        "profissao": None,
                        "nacionalidade": None,
                        "municipio": None,
                        "estado": None,
                        "cep": None,
                        "endereco": None,
                        "telefone": None,
                        "email": None,
                        "observacoes": None,
                        "origem": "ocr",
                    }
                )

        # =========================================================
        # DADOS DO IMÓVEL PRINCIPAL
        # =========================================================

        descricao_imovel = (
            dados_normalizados.get("descricao_imovel")
            or getattr(imovel, "descricao", None)
            or getattr(imovel, "nome", None)
        )

        area_total = (
            dados_normalizados.get("area_total")
            or getattr(imovel, "area_hectares", None)
        )

        unidade_area = (
            dados_normalizados.get("unidade_area")
            or "ha"
        )

        area_hectares = (
            dados_normalizados.get("area_hectares")
            or getattr(imovel, "area_hectares", None)
        )

        # =========================================================
        # CONFRONTANTES — ESTRUTURA ENRIQUECIDA
        # =========================================================

        confrontantes_payload: List[Dict[str, Any]] = []

        for idx, c in enumerate(confrontantes, start=1):

            nome = _safe(c.nome_confrontante)
            descricao = _safe(c.descricao)
            identificacao = _safe(c.identificacao_imovel_confrontante)
            matricula_cft = _safe(c.matricula_confrontante)

            tipo = _safe(getattr(c, "tipo", None))
            lote = _safe(getattr(c, "lote", None))
            gleba = _safe(getattr(c, "gleba", None))

            texto_base = (
                nome
                or identificacao
                or descricao
                or (f"MATRÍCULA {matricula_cft}" if matricula_cft else None)
                or "CONFRONTANTE NÃO IDENTIFICADO"
            )

            detalhamento_partes: List[str] = []

            if identificacao:
                detalhamento_partes.append(f"Imóvel: {identificacao}")

            if matricula_cft:
                detalhamento_partes.append(f"Matrícula: {matricula_cft}")

            if lote:
                detalhamento_partes.append(f"Lote: {lote}")

            if gleba:
                detalhamento_partes.append(f"Gleba: {gleba}")

            if tipo:
                detalhamento_partes.append(f"Tipo: {tipo}")

            if descricao:
                detalhamento_partes.append(descricao)

            detalhamento_final = (
                " | ".join(detalhamento_partes)
                if detalhamento_partes
                else texto_base
            )

            confrontantes_payload.append(
                {
                    "direcao": _safe(c.direcao),
                    "nome": nome,
                    "matricula": matricula_cft,
                    "descricao": descricao,
                    "identificacao": identificacao,

                    "lado": _safe(c.direcao),
                    "lado_normalizado": _safe(c.direcao_normalizada),
                    "ordem_segmento": c.ordem_segmento,
                    "lado_label": _safe(c.lado_label),

                    "confrontante": {
                        "nome": nome,
                        "matricula": matricula_cft,
                        "identificacao_imovel": identificacao,
                        "descricao": descricao,
                        "observacoes": _safe(c.observacoes),
                        "tipo": tipo,
                        "lote": lote,
                        "gleba": gleba,
                    },

                    "detalhamento": detalhamento_final,
                    "texto_resumo": texto_base,

                    "matricula_detalhada": {
                        "numero_matricula": matricula_cft,
                        "cartorio": None,
                        "comarca": None,
                        "area_total": None,
                        "unidade_area": None,
                        "area_hectares": None,
                        "proprietarios": [],
                    },
                }
            )

        # =========================================================
        # PAYLOAD FINAL (FORA DO FOR)
        # =========================================================

        return {
            "matricula": matricula.numero_matricula,
            "livro": matricula.livro,
            "folha": matricula.folha,
            "comarca": matricula.comarca,
            "codigo_cartorio": matricula.codigo_cartorio,
            "cartorio": (
                getattr(matricula, "cartorio", None).nome
                if getattr(matricula, "cartorio", None)
                else None
            ),
            "status": matricula.status,

            "numero_matricula": matricula.numero_matricula,
            "descricao_imovel": _safe(descricao_imovel),
            "area_total": area_total,
            "unidade_area": unidade_area,
            "area_hectares": area_hectares,

            "matricula_principal": {
                "numero_matricula": matricula.numero_matricula,
                "livro": _safe(matricula.livro),
                "folha": _safe(matricula.folha),
                "comarca": _safe(matricula.comarca),
                "cartorio": (
                    getattr(matricula, "cartorio", None).nome
                    if getattr(matricula, "cartorio", None)
                    else None
                ),
                "cartorio_id": getattr(
                    matricula,
                    "cartorio_id",
                    None,
                ),
                "codigo_cartorio": _safe(matricula.codigo_cartorio),
                "status": _safe(matricula.status),
                "arquivo_path": _safe(matricula.arquivo_path),
                "inteiro_teor": _safe(matricula.inteiro_teor),
                "observacoes": _safe(matricula.observacoes),
            },

            "imovel_principal": {
                "id": imovel.id,
                "nome": _safe(imovel.nome),
                "descricao": _safe(imovel.descricao),
                "area_hectares": getattr(imovel, "area_hectares", None),
                "ccir": _safe(getattr(imovel, "ccir", None)),
                "matricula_principal": _safe(getattr(imovel, "matricula_principal", None)),
            },

            "proprietarios": proprietarios,
            "confrontantes": confrontantes_payload,

            "metadata": {
                "origem": "matricula_ocr_processor_service",
                "possui_ocr": bool(dados_normalizados),
                "ocr_result_id": getattr(ocr, "id", None) if ocr else None,
                "documento_ocr_encontrado": bool(ocr),
                "total_confrontantes": len(confrontantes_payload),
                "total_proprietarios": len(proprietarios),
                "normalizado": True,
                "proprietarios_origem_banco": bool(proprietarios_db),
                "matricula_id": matricula.id,
                "imovel_id": imovel.id,
            }
        }
