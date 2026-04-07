from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.matricula import Matricula
from app.models.confrontante import Confrontante
from app.models.ocr_result import OcrResult

# 🔥 NOVOS IMPORTS
from app.services.memorial_parser_service import MemorialParserService
from app.services.memorial_service import MemorialService
from app.services.geometria_service import GeometriaService


class MatriculaOcrProcessorService:

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

            dados = MatriculaOcrProcessorService._parse_json(
                ocr.dados_extraidos_json
            )

            numero_matricula = (
                dados.get("numero_matricula")
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

            # =========================================================
            # CONFRONTANTES
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

            memorial_texto = dados.get("memorial_texto")

            if memorial_texto:

                parsed = MemorialParserService.gerar_geometria(memorial_texto)

                geojson = parsed.get("geojson")

                if geojson:
                    geometria = GeometriaService.salvar_geometria(
                        db=db,
                        imovel_id=matricula.imovel_id,
                        geojson=geojson
                    )

                    # gerar memorial TXT
                    MemorialService.gerar_memorial(
                        geometria_id=geometria.id,
                        geojson=geojson,
                        area_hectares=dados.get("area_total", 0),
                        perimetro_m=0,
                        imovel_id=matricula.imovel_id
                    )

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

    # =========================================================
    # CONFRONTANTES
    # =========================================================

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

            direcao = item.get("direcao")
            if not direcao:
                continue

            existente = (
                db.query(Confrontante)
                .filter(
                    Confrontante.imovel_id == imovel_id,
                    Confrontante.direcao == direcao
                )
                .first()
            )

            if existente:
                continue

            db.add(
                Confrontante(
                    imovel_id=imovel_id,
                    direcao=direcao,
                    nome_confrontante=item.get("nome"),
                    matricula_confrontante=item.get("matricula"),
                    identificacao_imovel_confrontante=item.get("identificacao"),
                    descricao=item.get("descricao"),
                )
            )

    # =========================================================
    # JSON PARSER
    # =========================================================

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

    # =========================================================
    # GERAR PAYLOAD PARA DOCX
    # =========================================================

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

        return {
            "matricula": matricula.numero_matricula,
            "livro": matricula.livro,
            "folha": matricula.folha,
            "comarca": matricula.comarca,
            "codigo_cartorio": matricula.codigo_cartorio,
            "status": matricula.status,
            "confrontantes": [
                {
                    "direcao": c.direcao,
                    "nome": c.nome_confrontante,
                    "matricula": c.matricula_confrontante,
                    "descricao": c.descricao
                }
                for c in confrontantes
            ]
        }