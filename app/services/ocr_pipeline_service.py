from __future__ import annotations

import json
import os
import re
from math import cos, radians, sin, sqrt
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
from app.services.geometria_service import GeometriaService
from app.services.memorial_parser_service import MemorialParserService
from app.services.memorial_service import MemorialService
from app.services.ocr_normalizer import normalizar_dados_ocr


class OcrPipelineService:
    FECHAMENTO_TOLERANCIA_METROS = 2.0

    @staticmethod
    def executar_pipeline(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados_extraidos: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "categoria": prompt_categoria,
            "steps": {},
            "errors": [],
        }

        if not prompt_categoria:
            result["errors"].append("Categoria de prompt ausente.")
            return result

        categoria = OcrPipelineService._normalizar_categoria(prompt_categoria)

        categorias_matricula = [
            "matricula_imovel",
            "analise_matricula_completa",
            "analise_matricula",
            "analise de matricula de imovel",
            "analise tecnica completa de matricula",
            "análise de matrícula de imóvel",
            "análise técnica completa de matrícula",
        ]

        categorias_matricula_normalizadas = [
            OcrPipelineService._normalizar_categoria(item)
            for item in categorias_matricula
        ]

        if categoria in categorias_matricula_normalizadas:
            dados_normalizados: dict[str, Any] = normalizar_dados_ocr(dados_extraidos)

            return OcrPipelineService._pipeline_matricula(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                dados=dados_normalizados,
            )

        result["errors"].append(
            f"Pipeline sem tratamento para categoria: {prompt_categoria}"
        )
        return result

    @staticmethod
    def _normalizar_categoria(texto: str) -> str:
        mapa = str.maketrans(
            "áàãâäéèêëíìîïóòõôöúùûüç",
            "aaaaaeeeeiiiiooooouuuuc",
        )
        return texto.lower().strip().translate(mapa)

    @staticmethod
    def _pipeline_matricula(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        dados: dict[str, Any],
    ) -> dict[str, Any]:
        print(f"🔎 Iniciando pipeline de matrícula para documento {document_id}")

        result: dict[str, Any] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "MATRICULA",
            "steps": {
                "matricula": {},
                "geometria": {},
                "memorial": {},
                "croqui": {},
                "cad": {},
                "sigef_csv": {},
            },
            "errors": [],
        }

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

        # =========================================================
        # MATRÍCULA
        # =========================================================
        try:
            matricula = OcrPipelineService._upsert_matricula(
                db=db,
                imovel=imovel,
                dados=dados,
            )

            if matricula:
                result["steps"]["matricula"] = {
                    "success": True,
                    "matricula_id": matricula.id,
                    "numero_matricula": matricula.numero_matricula,
                    "message": f"Matrícula pronta: {matricula.numero_matricula}",
                }
                print(f"✅ Matrícula pronta: {matricula.numero_matricula}")
            else:
                result["steps"]["matricula"] = {
                    "success": False,
                    "matricula_id": None,
                    "numero_matricula": None,
                    "message": "OCR não retornou número de matrícula.",
                }
                result["errors"].append("OCR não retornou número de matrícula.")
                print("⚠️ OCR não retornou número de matrícula")
        except Exception as exc:
            result["steps"]["matricula"] = {
                "success": False,
                "message": f"Falha ao upsert de matrícula: {str(exc)}",
            }
            result["errors"].append(str(exc))
            print(f"❌ Falha na matrícula: {str(exc)}")

        # =========================================================
        # GEOJSON / GEOMETRIA
        # =========================================================
        geojson = OcrPipelineService._resolver_geojson(dados)
        geometria: Optional[Geometria] = None
        tipo_referencial: Optional[str] = None

        if geojson:
            try:
                epsg_origem_inferido = 4326
                analise = GeometriaService.analisar_referencial(
                    geojson=geojson,
                    epsg_origem=epsg_origem_inferido,
                )

                tipo_referencial = str(analise["tipo_referencial"])

                if tipo_referencial == "LOCAL_CARTESIANA":
                    epsg_origem = 0
                else:
                    epsg_origem = 4326

                try:
                    epsg_utm, area_ha, perimetro_m = GeometriaService.calcular_area_perimetro(
                        geojson=geojson,
                        epsg_origem=epsg_origem,
                    )
                except Exception as exc:
                    print(f"⚠️ Falha na projeção UTM, aplicando fallback LOCAL: {str(exc)}")

                    geom_temp = analise["geom"]

                    epsg_utm = None

                    area_m2 = float(geom_temp.area or 0)
                    perimetro_m = float(geom_temp.length or 0)
                    area_ha = area_m2 / 10000.0

                geometria = Geometria(
                    imovel_id=imovel.id,
                    geojson=geojson,
                    epsg_origem=epsg_origem,
                    epsg_utm=epsg_utm,
                    area_hectares=area_ha,
                    perimetro_m=perimetro_m,
                    nome="Geometria derivada via OCR",
                    observacoes=(
                        "Gerada automaticamente a partir do OCR. "
                        f"Tipo referencial: {tipo_referencial}"
                    ),
                )

                db.add(geometria)
                db.commit()
                db.refresh(geometria)

                result["steps"]["geometria"] = {
                    "success": True,
                    "geometria_id": geometria.id,
                    "tipo_referencial": tipo_referencial,
                    "epsg_origem": geometria.epsg_origem,
                    "epsg_utm": geometria.epsg_utm,
                    "area_hectares": geometria.area_hectares,
                    "perimetro_m": geometria.perimetro_m,
                    "message": f"Geometria criada ID {geometria.id}",
                }

                print(f"✅ Geometria criada ID {geometria.id}")

            except Exception as exc:
                result["steps"]["geometria"] = {
                    "success": False,
                    "geometria_id": None,
                    "tipo_referencial": tipo_referencial,
                    "message": f"Falha ao calcular/persistir geometria: {str(exc)}",
                }
                result["errors"].append(f"Geometria: {str(exc)}")
                print(f"❌ Falha ao calcular geometria: {str(exc)}")
                geometria = None
        else:
            result["steps"]["geometria"] = {
                "success": False,
                "geometria_id": None,
                "tipo_referencial": None,
                "message": "Nenhuma geometria pôde ser gerada a partir do OCR.",
            }
            result["errors"].append("Nenhuma geometria pôde ser gerada a partir do OCR.")
            print("⚠️ Nenhuma geometria pôde ser gerada a partir do OCR")

        # =========================================================
        # MEMORIAL
        # =========================================================
        if geometria:
            try:
                memorial = MemorialService.gerar_memorial(
                    geometria_id=geometria.id,
                    geojson=geometria.geojson,
                    epsg_origem=geometria.epsg_origem,
                    area_hectares=geometria.area_hectares or imovel.area_hectares or 0,
                    perimetro_m=geometria.perimetro_m or 0,
                )

                result["steps"]["memorial"] = {
                    "success": True,
                    "tipo_referencial": memorial.get("tipo_referencial"),
                    "epsg_utm": memorial.get("epsg_utm"),
                    "linhas": len(memorial.get("linhas", [])),
                    "texto_preview": memorial.get("texto"),
                    "message": "Memorial descritivo gerado com sucesso.",
                }

                print("✅ Memorial descritivo gerado")
            except Exception as exc:
                result["steps"]["memorial"] = {
                    "success": False,
                    "message": f"Falha ao gerar memorial: {str(exc)}",
                }
                result["errors"].append(f"Memorial: {str(exc)}")
                print(f"❌ Falha ao gerar memorial: {str(exc)}")
        else:
            result["steps"]["memorial"] = {
                "success": False,
                "skipped": True,
                "message": "Memorial não executado: geometria inexistente.",
            }

        # =========================================================
        # CROQUI
        # =========================================================
        if geometria:
            try:
                base_url = "https://geoincra.escriturafacil.com"
                
                svg = CroquiService.gerar_svg(geometria.geojson)

                folder = f"app/uploads/imoveis/{imovel.id}/croqui"
                os.makedirs(folder, exist_ok=True)

                path_svg = f"{folder}/croqui_{geometria.id}.svg"

                with open(path_svg, "w", encoding="utf-8") as f:
                    f.write(svg)
            
                url_svg = f"{base_url}/{path_svg.replace('app/', '')}"

                result["steps"]["croqui"] = {
                    "success": True,
                    "arquivo_path": path_svg,
                    "arquivo_url": url_svg,
                    "message": f"Croqui salvo: {path_svg}",
                }

                print(f"✅ Croqui salvo: {path_svg}")
            except Exception as exc:
                result["steps"]["croqui"] = {
                    "success": False,
                    "message": f"Falha ao gerar croqui: {str(exc)}",
                }
                result["errors"].append(f"Croqui: {str(exc)}")
                print(f"❌ Falha ao gerar croqui: {str(exc)}")
        else:
            result["steps"]["croqui"] = {
                "success": False,
                "skipped": True,
                "message": "Croqui não executado: geometria inexistente.",
            }

        # =========================================================
        # CAD / SCR
        # =========================================================
        if geometria:
            try:
                scr = CadExportService.gerar_scr(geometria.geojson)
                path_scr = CadExportService.salvar_scr(
                    imovel_id=imovel.id,
                    scr=scr,
                )

                url_scr = f"{base_url}/{path_scr.replace('app/', '')}"

                result["steps"]["cad"] = {
                    "success": True,
                    "arquivo_path": path_scr,
                    "arquivo_url": url_scr,
                    "message": f"Script CAD salvo: {path_scr}",
                }

                print(f"✅ Script CAD salvo: {path_scr}")
            except Exception as exc:
                result["steps"]["cad"] = {
                    "success": False,
                    "message": f"Falha ao gerar CAD: {str(exc)}",
                }
                result["errors"].append(f"CAD: {str(exc)}")
                print(f"❌ Falha ao gerar CAD: {str(exc)}")
        else:
            result["steps"]["cad"] = {
                "success": False,
                "skipped": True,
                "message": "CAD não executado: geometria inexistente.",
            }

        # =========================================================
        # SIGEF CSV
        # =========================================================
        if geometria:
            if geometria.epsg_origem and geometria.epsg_origem > 0:
                try:
                    payload = SigefCsvExportRequest(
                        geometria_id=geometria.id,
                        prefixo_vertice="V",
                        document_group_key="PLANILHA_SIGEF",
                        tipo="Planilha SIGEF",
                        observacoes_tecnicas=None,
                        incluir_conteudo=False,
                    )

                    sigef_data = exportar_sigef_csv(db, payload)

                    path_sigef = sigef_data.get("arquivo_path")
                    url_sigef = f"{base_url}/{path_sigef.replace('app/', '')}" if path_sigef else None

                    result["steps"]["sigef_csv"] = {
                        "success": True,
                        "documento_tecnico_id": sigef_data.get("documento_tecnico_id"),
                        "arquivo_path": path_sigef,
                        "arquivo_url": url_sigef,
                        "epsg_utm": sigef_data.get("epsg_utm"),
                        "message": "Planilha SIGEF gerada com sucesso.",
                    }

                    print("✅ Planilha SIGEF gerada")
                except Exception as exc:
                    result["steps"]["sigef_csv"] = {
                        "success": False,
                        "message": f"Falha ao gerar SIGEF CSV: {str(exc)}",
                    }
                    result["errors"].append(f"SIGEF CSV: {str(exc)}")
                    print(f"❌ Falha ao gerar SIGEF CSV: {str(exc)}")
            else:
                result["steps"]["sigef_csv"] = {
                    "success": False,
                    "skipped": True,
                    "message": (
                        "SIGEF CSV não executado: geometria local/cartesiana "
                        "não é exportável como SIGEF oficial."
                    ),
                }
                print("ℹ️ SIGEF CSV ignorado: geometria local/cartesiana")
        else:
            result["steps"]["sigef_csv"] = {
                "success": False,
                "skipped": True,
                "message": "SIGEF CSV não executado: geometria inexistente.",
            }

        # =========================================================
        # SUCESSO FINAL
        # =========================================================
        geometria_ok = bool(result["steps"]["geometria"].get("success"))
        memorial_ok = bool(result["steps"]["memorial"].get("success"))
        croqui_ok = bool(result["steps"]["croqui"].get("success"))
        cad_ok = bool(result["steps"]["cad"].get("success"))

        if geometria and geometria.epsg_origem and geometria.epsg_origem > 0:
            sigef_ok = bool(result["steps"]["sigef_csv"].get("success"))
            result["success"] = geometria_ok and memorial_ok and croqui_ok and cad_ok and sigef_ok
        else:
            result["success"] = geometria_ok and memorial_ok and croqui_ok and cad_ok

        print("🏁 Pipeline OCR concluído")
        return result

    @staticmethod
    def _upsert_matricula(
        db: Session,
        imovel: Imovel,
        dados: dict[str, Any],
    ) -> Optional[Matricula]:

        numero_matricula: Optional[str] = None

        # 🔹 PRIORIDADE: dados normalizados
        if isinstance(dados.get("matricula"), dict):
            numero_matricula = dados["matricula"].get("numero")

        # 🔹 FALLBACK: estrutura antiga
        if not numero_matricula:
            numero_matricula = dados.get("numero_matricula") or dados.get("matricula")

        if not numero_matricula:
            return None

        matricula: Optional[Matricula] = (
            db.query(Matricula)
            .filter(
                Matricula.imovel_id == imovel.id,
                Matricula.numero_matricula == numero_matricula,
            )
            .first()
        )

        # 🔹 Compatível com normalizer + legado
        descricao_imovel: Optional[str] = (
            dados.get("descricao_imovel")
            or (
                dados.get("imovel", {}).get("descricao")
                if isinstance(dados.get("imovel"), dict)
                else None
            )
        )

        comarca: Optional[str] = (
            dados.get("comarca")
            or (
                dados.get("matricula", {}).get("comarca")
                if isinstance(dados.get("matricula"), dict)
                else None
            )
        )

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

        alterou: bool = False

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

@staticmethod
def _resolver_geojson(dados: dict[str, Any]) -> Optional[str]:
    # 1️⃣ GeoJSON direto (prioridade máxima)
    geojson = dados.get("geojson") or dados.get("geometria")

    geojson_normalizado = OcrPipelineService._normalizar_geojson(geojson)
    if geojson_normalizado:
        print("✅ GeoJSON recebido diretamente do OCR")
        return geojson_normalizado

    # 2️⃣ Segmentos NORMALIZADOS (novo padrão do worker)
    segmentos_memorial = None

    if isinstance(dados.get("geometria"), dict):
        segmentos_memorial = dados["geometria"].get("segmentos")

    if not segmentos_memorial:
        segmentos_memorial = dados.get("segmentos_memorial")

    geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
        segmentos_memorial
    )

    if geojson_por_segmentos:
        print("✅ GeoJSON gerado a partir de segmentos")
        return geojson_por_segmentos

    # 3️⃣ Memorial texto (fallback final)
    memorial_texto = None

    if isinstance(dados.get("geometria"), dict):
        memorial_texto = dados["geometria"].get("memorial_texto")

    if not memorial_texto:
        memorial_texto = dados.get("memorial_texto")

    geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
        memorial_texto
    )

    if geojson_por_memorial:
        print("✅ GeoJSON gerado a partir de memorial_texto")
        return geojson_por_memorial

    print("❌ Nenhuma fonte geométrica válida encontrada")
    return None

@staticmethod
def _normalizar_geojson(geojson: Any) -> Optional[str]:
    if geojson is None:
        return None

    if isinstance(geojson, dict):
        try:
            return json.dumps(geojson)
        except Exception:
            return None

    if isinstance(geojson, str):
        texto = geojson.strip()

        if not texto:
            return None

        try:
            json.loads(texto)
            return texto
        except Exception:
            print("⚠️ GeoJSON inválido recebido do OCR")
            return None

    return None


@staticmethod
def _distancia_entre_pontos(
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> float:
    dx: float = float(p2[0]) - float(p1[0])
    dy: float = float(p2[1]) - float(p1[1])
    return sqrt((dx * dx) + (dy * dy))


@staticmethod
def _fechar_anel(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(coords) < 3:
        return coords

    primeiro: tuple[float, float] = coords[0]
    ultimo: tuple[float, float] = coords[-1]

    distancia_fechamento = OcrPipelineService._distancia_entre_pontos(
        primeiro,
        ultimo,
    )

    if distancia_fechamento <= OcrPipelineService.FECHAMENTO_TOLERANCIA_METROS:
        coords[-1] = primeiro
        return coords

    if primeiro != ultimo:
        coords.append(primeiro)

    return coords

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
            print(f"⚠️ Segmento inválido na posição {index}")
            return None

        angulo_raw = (
            seg.get("azimute")
            or seg.get("azimute_raw")
            or seg.get("rumo")
        )

        distancia_raw = seg.get("distancia")

        if angulo_raw is None or distancia_raw is None:
            print(f"⚠️ Segmento incompleto na posição {index}")
            return None

        try:
            azimute = OcrPipelineService._parse_angulo_para_graus(str(angulo_raw))

            if azimute < 0 or azimute > 360:
                raise ValueError("Azimute fora do intervalo válido")

            distancia = OcrPipelineService._parse_distancia(distancia_raw)

            if distancia <= 0:
                raise ValueError("Distância inválida")

        except Exception as exc:
            print(f"⚠️ Segmento inválido {index}: {str(exc)}")
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

    coords = OcrPipelineService._fechar_anel(coords)

    polygon = Polygon(coords)

    if polygon.is_empty or not polygon.is_valid:
        polygon = polygon.buffer(0)

    if polygon.is_empty or not polygon.is_valid:
        print("⚠️ Polígono inválido mesmo após correção")
        return None

    return json.dumps(polygon.__geo_interface__)

@staticmethod
def _gerar_geojson_por_memorial(
    memorial_texto: Any,
) -> Optional[str]:
    if not isinstance(memorial_texto, str):
        return None

    texto = memorial_texto.strip()

    if not texto:
        return None

    try:
        resultado = MemorialParserService.gerar_geometria(texto)
    except Exception as exc:
        print(f"⚠️ Falha ao gerar geometria a partir do memorial: {str(exc)}")
        return None

    geojson = resultado.get("geojson")

    if not isinstance(geojson, dict):
        return None

    try:
        return json.dumps(geojson)
    except Exception:
        return None


@staticmethod
def _parse_distancia(valor: Any) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if not texto:
        raise ValueError("Distância vazia")

    texto = texto.replace(".", "").replace(",", ".")

    try:
        distancia = float(texto)
    except Exception:
        raise ValueError(f"Distância inválida: {valor}")

    if distancia <= 0:
        raise ValueError("Distância deve ser positiva")

    return distancia

@staticmethod
def _parse_angulo_para_graus(valor: str) -> float:
    valor_limpo = " ".join(valor.strip().upper().split())

    # RUMO (N 10° E)
    if re.match(r"^[NS]\s*.+\s*[EW]$", valor_limpo):
        return MemorialParserService._rumo_para_azimute(valor_limpo)

    # DMS
    match_dms = re.search(
        r"(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?",
        valor_limpo,
    )

    if match_dms:
        graus, minutos, segundos = match_dms.groups()

        g = float(graus)
        m = float(minutos)
        s = float(segundos or 0)

        decimal = g + (m / 60) + (s / 3600)

        if decimal < 0 or decimal > 360:
            raise ValueError("Ângulo DMS inválido")

        return decimal

    # FLOAT DIRETO
    try:
        decimal = float(valor_limpo.replace(",", "."))
        if decimal < 0 or decimal > 360:
            raise ValueError("Ângulo fora do intervalo")
        return decimal
    except Exception:
        raise ValueError(f"Ângulo inválido: {valor}")