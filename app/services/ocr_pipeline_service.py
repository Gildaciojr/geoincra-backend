# app/services/ocr_pipeline_service.py

from __future__ import annotations

import json
import os
import re
from math import cos, radians, sin
from typing import Any, Optional

from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.crud.sigef_export_crud import exportar_sigef_csv
from app.models.document import Document
from app.models.geometria import Geometria
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.schemas.sigef_export import SigefCsvExportRequest
from app.services.cad_export_service import CadExportService
from app.services.croqui_service import CroquiService
from app.services.memorial_parser_service import MemorialParserService
from app.services.memorial_service import MemorialService


class OcrPipelineService:
    """
    Pipeline pós-OCR responsável por transformar dados estruturados
    em entidades técnicas do sistema.

    Fluxo completo:

    OCR
      ↓
    Interpretação OpenAI
      ↓
    Matrícula
      ↓
    Geometria
      ↓
    Memorial Descritivo
      ↓
    Croqui SVG
      ↓
    Script CAD
      ↓
    Planilha SIGEF
    """

    # =========================================================
    # ENTRYPOINT
    # =========================================================

    @staticmethod
    def executar_pipeline(
        db: Session,
        document_id: int,
        prompt_categoria: str,
        dados_extraidos: dict[str, Any],
    ) -> bool | None:
        if not prompt_categoria:
            print("⚠️ Pipeline ignorado: categoria de prompt ausente")
            return None

        categoria = prompt_categoria.lower().strip()

        categorias_matricula = [
            "matricula_imovel",
            "analise_matricula_completa",
            "analise_matricula",
            "analise de matricula de imovel",
            "analise tecnica completa de matricula",
            "análise de matrícula de imóvel",
            "análise técnica completa de matrícula",
        ]

        if categoria in categorias_matricula:
            return OcrPipelineService._pipeline_matricula(
                db=db,
                document_id=document_id,
                dados=dados_extraidos,
            )

        print(f"ℹ️ Pipeline sem tratamento para categoria: {categoria}")
        return None

    # =========================================================
    # PIPELINE MATRÍCULA
    # =========================================================

    @staticmethod
    def _pipeline_matricula(
        db: Session,
        document_id: int,
        dados: dict[str, Any],
    ) -> bool:
        print(f"🔎 Iniciando pipeline de matrícula para documento {document_id}")

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise Exception("Documento não encontrado")

        imovel: Optional[Imovel] = (
            db.query(Imovel)
            .filter(Imovel.project_id == doc.project_id)
            .first()
        )
        if not imovel:
            raise Exception("Projeto não possui imóvel cadastrado")

        # -----------------------------------------------------
        # MATRÍCULA
        # -----------------------------------------------------

        matricula = OcrPipelineService._upsert_matricula(
            db=db,
            imovel=imovel,
            dados=dados,
        )

        if matricula:
            print(f"✅ Matrícula pronta: {matricula.numero_matricula}")
        else:
            print("⚠️ OCR não retornou número de matrícula")

        # -----------------------------------------------------
        # GEOMETRIA
        # -----------------------------------------------------

        geojson = OcrPipelineService._resolver_geojson(dados)

        geometria: Optional[Geometria] = None

        if geojson:
            geometria = Geometria(
                imovel_id=imovel.id,
                geojson=geojson,
                epsg_origem=4326,
            )

            db.add(geometria)
            db.commit()
            db.refresh(geometria)

            print(f"✅ Geometria criada ID {geometria.id}")
        else:
            print("⚠️ Nenhuma geometria pôde ser gerada a partir do OCR")

        # -----------------------------------------------------
        # MEMORIAL
        # -----------------------------------------------------

        if geometria:
            memorial = MemorialService.gerar_memorial(
                geometria_id=geometria.id,
                geojson=geometria.geojson,
                area_hectares=geometria.area_hectares or imovel.area_hectares or 0,
                perimetro_m=geometria.perimetro_m or 0,
            )
            print("✅ Memorial descritivo gerado")
            _ = memorial

        # -----------------------------------------------------
        # CROQUI SVG
        # -----------------------------------------------------

        if geometria:
            svg = CroquiService.gerar_svg(geometria.geojson)

            folder = f"app/uploads/imoveis/{imovel.id}/croqui"
            os.makedirs(folder, exist_ok=True)

            path_svg = f"{folder}/croqui_{geometria.id}.svg"

            with open(path_svg, "w", encoding="utf-8") as f:
                f.write(svg)

            print(f"✅ Croqui salvo: {path_svg}")

        # -----------------------------------------------------
        # CAD SCRIPT
        # -----------------------------------------------------

        if geometria:
            scr = CadExportService.gerar_scr(geometria.geojson)

            path_scr = CadExportService.salvar_scr(
                imovel_id=imovel.id,
                scr=scr,
            )

            print(f"✅ Script CAD salvo: {path_scr}")

        # -----------------------------------------------------
        # SIGEF EXPORT
        # -----------------------------------------------------

        if geometria:
            payload = SigefCsvExportRequest(
                geometria_id=geometria.id,
                prefixo_vertice="V",
                document_group_key="PLANILHA_SIGEF",
                tipo="Planilha SIGEF",
                observacoes_tecnicas=None,
                incluir_conteudo=False,
            )

            exportar_sigef_csv(db, payload)
            print("✅ Planilha SIGEF gerada")

        print("🏁 Pipeline OCR concluído")
        return True

    # =========================================================
    # MATRÍCULA HELPERS
    # =========================================================

    @staticmethod
    def _upsert_matricula(
        db: Session,
        imovel: Imovel,
        dados: dict[str, Any],
    ) -> Optional[Matricula]:
        numero_matricula = (
            dados.get("numero_matricula")
            or dados.get("matricula")
        )

        if not numero_matricula:
            return None

        matricula = (
            db.query(Matricula)
            .filter(
                Matricula.imovel_id == imovel.id,
                Matricula.numero_matricula == numero_matricula,
            )
            .first()
        )

        descricao_imovel = dados.get("descricao_imovel")
        comarca = dados.get("comarca")

        if not matricula:
            matricula = Matricula(
                imovel_id=imovel.id,
                numero_matricula=numero_matricula,
                comarca=comarca,
                inteiro_teor=descricao_imovel,
            )

            db.add(matricula)
            db.commit()
            db.refresh(matricula)

            print(f"✅ Matrícula criada: {numero_matricula}")
            return matricula

        alterou = False

        if comarca and not matricula.comarca:
            matricula.comarca = comarca
            alterou = True

        if descricao_imovel and not matricula.inteiro_teor:
            matricula.inteiro_teor = descricao_imovel
            alterou = True

        if alterou:
            db.commit()
            db.refresh(matricula)
            print(f"ℹ️ Matrícula atualizada: {numero_matricula}")
        else:
            print(f"ℹ️ Matrícula já existente: {numero_matricula}")

        return matricula

    # =========================================================
    # GEOMETRIA HELPERS
    # =========================================================

    @staticmethod
    def _resolver_geojson(dados: dict[str, Any]) -> Optional[str]:
        """
        Resolve a geometria em ordem de prioridade:

        1. geojson
        2. geometria
        3. segmentos_memorial
        4. memorial_texto
        """
        geojson = dados.get("geojson") or dados.get("geometria")

        geojson_normalizado = OcrPipelineService._normalizar_geojson(geojson)
        if geojson_normalizado:
            print("✅ GeoJSON recebido diretamente do OCR")
            return geojson_normalizado

        segmentos_memorial = dados.get("segmentos_memorial")
        geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
            segmentos_memorial
        )
        if geojson_por_segmentos:
            print("✅ GeoJSON gerado a partir de segmentos_memorial")
            return geojson_por_segmentos

        memorial_texto = dados.get("memorial_texto")
        geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
            memorial_texto
        )
        if geojson_por_memorial:
            print("✅ GeoJSON gerado a partir de memorial_texto")
            return geojson_por_memorial

        return None

    @staticmethod
    def _normalizar_geojson(geojson: Any) -> Optional[str]:
        if not geojson:
            return None

        if isinstance(geojson, dict):
            try:
                return json.dumps(geojson)
            except Exception:
                return None

        if isinstance(geojson, str):
            try:
                json.loads(geojson)
                return geojson
            except Exception:
                print("⚠️ GeoJSON inválido recebido do OCR")
                return None

        return None

    @staticmethod
    def _gerar_geojson_por_segmentos(
        segmentos_memorial: Any,
    ) -> Optional[str]:
        if not isinstance(segmentos_memorial, list) or not segmentos_memorial:
            return None

        coords: list[tuple[float, float]] = [(0.0, 0.0)]
        x = 0.0
        y = 0.0

        for index, seg in enumerate(segmentos_memorial, start=1):
            if not isinstance(seg, dict):
                print(f"⚠️ Segmento inválido na posição {index}: não é objeto")
                return None

            angulo_raw = (
                seg.get("azimute")
                or seg.get("rumo")
                or seg.get("angulo")
            )

            distancia_raw = seg.get("distancia")

            if angulo_raw is None or distancia_raw is None:
                print(f"⚠️ Segmento incompleto na posição {index}")
                return None

            try:
                azimute = OcrPipelineService._parse_angulo_para_graus(
                    str(angulo_raw)
                )
                distancia = OcrPipelineService._parse_distancia(
                    distancia_raw
                )
            except Exception as exc:
                print(
                    f"⚠️ Falha ao interpretar segmento {index}: {str(exc)}"
                )
                return None

            azimute_rad = radians(azimute)

            dx = distancia * sin(azimute_rad)
            dy = distancia * cos(azimute_rad)

            x += dx
            y += dy

            coords.append((x, y))

        if len(coords) < 4:
            print("⚠️ Segmentos insuficientes para formar polígono")
            return None

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        polygon = Polygon(coords)

        if polygon.is_empty or not polygon.is_valid:
            print("⚠️ Polígono inválido gerado a partir dos segmentos")
            return None

        return json.dumps(polygon.__geo_interface__)

    @staticmethod
    def _gerar_geojson_por_memorial(
        memorial_texto: Any,
    ) -> Optional[str]:
        if not isinstance(memorial_texto, str) or not memorial_texto.strip():
            return None

        try:
            resultado = MemorialParserService.gerar_geometria(
                memorial_texto.strip()
            )
        except Exception as exc:
            print(
                f"⚠️ Falha ao gerar geometria a partir do memorial: {str(exc)}"
            )
            return None

        geojson = resultado.get("geojson")
        if not geojson:
            return None

        return json.dumps(geojson)

    @staticmethod
    def _parse_distancia(valor: Any) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        # remove separador de milhar e padroniza decimal
        texto = texto.replace(".", "").replace(",", ".")

        return float(texto)

    @staticmethod
    def _parse_angulo_para_graus(valor: str) -> float:
        """
        Aceita:
        - azimute DMS: 01°22'35"
        - rumo quadrantal: N 45°00'00" E
        - decimal simples
        """
        valor_limpo = " ".join(valor.strip().upper().split())

        if re.match(r"^[NS]\s*.+\s*[EW]$", valor_limpo):
            return MemorialParserService._rumo_para_azimute(valor_limpo)

        match_dms = re.search(
            r"(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?",
            valor_limpo,
        )
        if match_dms:
            graus, minutos, segundos = match_dms.groups()
            g = float(graus)
            m = float(minutos)
            s = float(segundos or 0)
            return g + (m / 60) + (s / 3600)

        return float(valor_limpo.replace(",", "."))