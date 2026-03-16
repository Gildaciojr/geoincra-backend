# app/services/ocr_pipeline_service.py

from __future__ import annotations

import json
import os
from typing import Optional

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.models.geometria import Geometria

from app.schemas.sigef_export import SigefCsvExportRequest
from app.crud.sigef_export_crud import exportar_sigef_csv

from app.services.memorial_service import MemorialService
from app.services.croqui_service import CroquiService
from app.services.cad_export_service import CadExportService
from app.services.memorial_parser_service import MemorialParserService


class OcrPipelineService:

    @staticmethod
    def executar_pipeline(
        db: Session,
        document_id: int,
        prompt_categoria: str,
        dados_extraidos: dict,
    ):

        if not prompt_categoria:
            return None

        categoria = prompt_categoria.lower().strip()

        categorias_matricula = [
            "matricula_imovel",
            "analise_matricula_completa",
            "analise_matricula",
            "analise de matricula de imovel",
            "analise tecnica completa de matricula",
        ]

        if categoria in categorias_matricula:
            return OcrPipelineService._pipeline_matricula(
                db,
                document_id,
                dados_extraidos,
            )

        return None

    # -----------------------------------------------------
    # PIPELINE MATRÍCULA
    # -----------------------------------------------------

    @staticmethod
    def _pipeline_matricula(
        db: Session,
        document_id: int,
        dados: dict,
    ):

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

        # -------------------------------------------------
        # MATRÍCULA
        # -------------------------------------------------

        numero_matricula = (
            dados.get("numero_matricula")
            or dados.get("matricula")
        )

        matricula: Optional[Matricula] = None

        if numero_matricula:

            matricula = (
                db.query(Matricula)
                .filter(
                    Matricula.imovel_id == imovel.id,
                    Matricula.numero_matricula == numero_matricula,
                )
                .first()
            )

            if not matricula:

                matricula = Matricula(
                    imovel_id=imovel.id,
                    numero_matricula=numero_matricula,
                    comarca=dados.get("comarca"),
                    inteiro_teor=dados.get("descricao_imovel"),
                )

                db.add(matricula)
                db.commit()
                db.refresh(matricula)

                print(f"✅ Matrícula criada: {numero_matricula}")

        # -------------------------------------------------
        # GEOMETRIA
        # -------------------------------------------------

        geojson = dados.get("geojson") or dados.get("geometria")

        if isinstance(geojson, dict):
            geojson = json.dumps(geojson)

        # fallback: gerar a partir do memorial
        if not geojson:

            memorial_texto = dados.get("memorial_texto")

            if memorial_texto:

                try:

                    resultado = MemorialParserService.gerar_geometria(
                        memorial_texto
                    )

                    geojson = json.dumps(resultado["geojson"])

                    print("✅ GeoJSON gerado a partir do memorial")

                except Exception as e:

                    print("⚠️ Falha ao gerar geometria do memorial:", str(e))

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

        # -------------------------------------------------
        # MEMORIAL
        # -------------------------------------------------

        if geometria:

            memorial = MemorialService.gerar_memorial(
                geometria_id=geometria.id,
                geojson=geometria.geojson,
                area_hectares=geometria.area_hectares or imovel.area_hectares,
                perimetro_m=geometria.perimetro_m or 0,
            )

            print("✅ Memorial descritivo gerado")

        # -------------------------------------------------
        # CROQUI
        # -------------------------------------------------

        if geometria:

            svg = CroquiService.gerar_svg(geometria.geojson)

            folder = f"app/uploads/imoveis/{imovel.id}/croqui"

            os.makedirs(folder, exist_ok=True)

            path_svg = f"{folder}/croqui_{geometria.id}.svg"

            with open(path_svg, "w") as f:
                f.write(svg)

            print(f"✅ Croqui salvo: {path_svg}")

        # -------------------------------------------------
        # CAD
        # -------------------------------------------------

        if geometria:

            scr = CadExportService.gerar_scr(geometria.geojson)

            path_scr = CadExportService.salvar_scr(
                imovel_id=imovel.id,
                scr=scr,
            )

            print(f"✅ Script CAD salvo: {path_scr}")

        # -------------------------------------------------
        # SIGEF
        # -------------------------------------------------

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