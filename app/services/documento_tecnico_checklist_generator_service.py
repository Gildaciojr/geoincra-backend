from __future__ import annotations

from typing import Optional, TypedDict

from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import (
    DocumentoTecnicoChecklist,
)


class ChecklistTemplateItem(TypedDict):
    chave: str
    descricao: str
    obrigatorio: bool


class DocumentoTecnicoChecklistGeneratorService:

    # =========================================================
    # TEMPLATES BASE
    # =========================================================
    CHECKLISTS: dict[str, list[ChecklistTemplateItem]] = {

        # =====================================================
        # CROQUI
        # =====================================================
        "CROQUI": [
            {
                "chave": "GEOMETRIA_VALIDA",
                "descricao": "Geometria do imóvel válida",
                "obrigatorio": True,
            },
            {
                "chave": "AREA_PRESENTE",
                "descricao": "Área total identificada",
                "obrigatorio": True,
            },
            {
                "chave": "CONFRONTANTES_PRESENTES",
                "descricao": "Confrontantes identificados",
                "obrigatorio": True,
            },
            {
                "chave": "VERTICES_PRESENTES",
                "descricao": "Vértices técnicos presentes",
                "obrigatorio": True,
            },
            {
                "chave": "AZIMUTES_PRESENTES",
                "descricao": "Azimutes calculados",
                "obrigatorio": True,
            },
        ],

        # =====================================================
        # MEMORIAL
        # =====================================================
        "MEMORIAL": [
            {
                "chave": "MEMORIAL_COORDENADAS",
                "descricao": "Coordenadas do memorial presentes",
                "obrigatorio": True,
            },
            {
                "chave": "MEMORIAL_AZIMUTES",
                "descricao": "Azimutes do memorial presentes",
                "obrigatorio": True,
            },
            {
                "chave": "MEMORIAL_DISTANCIAS",
                "descricao": "Distâncias do memorial presentes",
                "obrigatorio": True,
            },
        ],

        # =====================================================
        # SIGEF
        # =====================================================
        "SIGEF": [
            {
                "chave": "SIGEF_ART",
                "descricao": "ART vinculada ao SIGEF",
                "obrigatorio": True,
            },
            {
                "chave": "SIGEF_DATUM",
                "descricao": "Datum geodésico identificado",
                "obrigatorio": True,
            },
        ],

        # =====================================================
        # MATRÍCULA
        # =====================================================
        "MATRICULA": [
            {
                "chave": "MATRICULA_NUMERO",
                "descricao": "Número da matrícula identificado",
                "obrigatorio": True,
            },
            {
                "chave": "MATRICULA_PROPRIETARIO",
                "descricao": "Proprietário identificado",
                "obrigatorio": True,
            },
            {
                "chave": "MATRICULA_CONFRONTANTES",
                "descricao": "Confrontantes identificados",
                "obrigatorio": True,
            },
        ],

        # =====================================================
        # GEOJSON
        # =====================================================
        "GEOJSON": [
            {
                "chave": "GEOJSON_VALIDO",
                "descricao": "GeoJSON válido",
                "obrigatorio": True,
            },
            {
                "chave": "AREA_CALCULADA",
                "descricao": "Área georreferenciada calculada",
                "obrigatorio": True,
            },
            {
                "chave": "PERIMETRO_CALCULADO",
                "descricao": "Perímetro calculado",
                "obrigatorio": True,
            },
        ],

        # =====================================================
        # CAD / DXF / SHP
        # =====================================================
        "CAD": [
            {
                "chave": "ARQUIVO_CAD_VALIDO",
                "descricao": "Arquivo CAD válido",
                "obrigatorio": True,
            },
            {
                "chave": "CAMADAS_TECNICAS",
                "descricao": "Camadas técnicas identificadas",
                "obrigatorio": False,
            },
        ],
    }

    @staticmethod
    def _normalizar_tipo_documento(
        documento: DocumentoTecnico,
    ) -> Optional[str]:

        if not documento:
            return None

        tipo_documento = (
            str(documento.tipo or "")
            .strip()
            .upper()
        )

        mapa_tipos = {
            "MATRÍCULA PDF": "MATRICULA",
            "MATRICULA PDF": "MATRICULA",
            "MATRÍCULA": "MATRICULA",
            "MATRICULA": "MATRICULA",

            "CROQUI": "CROQUI",

            "MEMORIAL": "MEMORIAL",
            "MEMORIAL DESCRITIVO": "MEMORIAL",

            "SIGEF CSV": "SIGEF",
            "SIGEF": "SIGEF",

            "GEOJSON": "GEOJSON",
            "GEOMETRIA": "GEOJSON",

            "DXF": "CAD",
            "CAD": "CAD",
            "SHP": "CAD",
            "SHAPEFILE": "CAD",
        }

        return mapa_tipos.get(
            tipo_documento,
            tipo_documento,
        )

    @staticmethod
    def _metadata(
        documento: DocumentoTecnico,
    ) -> dict:

        metadata = getattr(
            documento,
            "metadata_json",
            None,
        )

        if isinstance(metadata, dict):
            return metadata

        return {}

    @staticmethod
    def _tem_valor(
        valor: object,
    ) -> bool:

        if valor is None:
            return False

        if isinstance(valor, bool):
            return valor

        if isinstance(valor, (int, float)):
            return valor > 0

        if isinstance(valor, str):
            return bool(valor.strip())

        if isinstance(valor, (list, tuple, set, dict)):
            return len(valor) > 0

        return True

    @staticmethod
    def _resolver_status_inicial(
        documento: DocumentoTecnico,
        chave: str,
    ) -> tuple[str, str, str]:

        metadata = (
            DocumentoTecnicoChecklistGeneratorService
            ._metadata(documento)
        )

        conteudo_json = getattr(
            documento,
            "conteudo_json",
            None,
        )

        arquivo_path = getattr(
            documento,
            "arquivo_path",
            None,
        )

        # =====================================================
        # GEOJSON / GEOMETRIA
        # =====================================================
        if chave in {
            "GEOJSON_VALIDO",
            "GEOMETRIA_VALIDA",
        }:

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(arquivo_path)
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(conteudo_json)
            ):
                return (
                    "OK",
                    "Geometria identificada automaticamente.",
                    "ALTA",
                )

            return (
                "ERRO",
                "Geometria não identificada no documento técnico.",
                "ALTA",
            )

        if chave in {
            "AREA_PRESENTE",
            "AREA_CALCULADA",
        }:

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("area_hectares"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("area_ha"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("area_m2"))
            ):
                return (
                    "OK",
                    "Área identificada automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Área não encontrada nos metadados do documento.",
                "MEDIA",
            )

        if chave == "PERIMETRO_CALCULADO":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("perimetro_m"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("perimetro"))
            ):
                return (
                    "OK",
                    "Perímetro identificado automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Perímetro não encontrado nos metadados do documento.",
                "MEDIA",
            )

        # =====================================================
        # CROQUI
        # =====================================================
        if chave in {
            "VERTICES_PRESENTES",
            "AZIMUTES_PRESENTES",
        }:
            return (
                "NA",
                "Item criado automaticamente para conferência técnica.",
                "MEDIA",
            )

        if chave == "CONFRONTANTES_PRESENTES":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("total_confrontantes"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("confrontantes"))
            ):
                return (
                    "OK",
                    "Confrontantes identificados automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Confrontantes não identificados automaticamente.",
                "MEDIA",
            )

        # =====================================================
        # MEMORIAL
        # =====================================================
        if chave in {
            "MEMORIAL_COORDENADAS",
            "MEMORIAL_AZIMUTES",
            "MEMORIAL_DISTANCIAS",
        }:
            return (
                "NA",
                "Item criado automaticamente para validação do memorial.",
                "MEDIA",
            )

        # =====================================================
        # SIGEF
        # =====================================================
        if chave == "SIGEF_ART":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("art"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("numero_art"))
            ):
                return (
                    "OK",
                    "ART identificada automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "ART não identificada nos metadados SIGEF.",
                "MEDIA",
            )

        if chave == "SIGEF_DATUM":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("datum"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("sistema_geodesico"))
            ):
                return (
                    "OK",
                    "Datum geodésico identificado automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Datum geodésico não identificado nos metadados.",
                "MEDIA",
            )

        # =====================================================
        # MATRÍCULA
        # =====================================================
        if chave == "MATRICULA_NUMERO":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("numero_matricula"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("matricula"))
            ):
                return (
                    "OK",
                    "Número da matrícula identificado automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Número da matrícula não identificado nos metadados.",
                "MEDIA",
            )

        if chave == "MATRICULA_PROPRIETARIO":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("proprietario"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("proprietario_nome"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("proprietarios"))
            ):
                return (
                    "OK",
                    "Proprietário identificado automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Proprietário não identificado nos metadados.",
                "MEDIA",
            )

        if chave == "MATRICULA_CONFRONTANTES":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("confrontantes"))
                or DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(metadata.get("total_confrontantes"))
            ):
                return (
                    "OK",
                    "Confrontantes identificados automaticamente.",
                    "ALTA",
                )

            return (
                "ALERTA",
                "Confrontantes não identificados nos metadados.",
                "MEDIA",
            )

        # =====================================================
        # CAD
        # =====================================================
        if chave == "ARQUIVO_CAD_VALIDO":

            if (
                DocumentoTecnicoChecklistGeneratorService
                ._tem_valor(arquivo_path)
            ):
                return (
                    "OK",
                    "Arquivo técnico gerado automaticamente.",
                    "ALTA",
                )

            return (
                "ERRO",
                "Arquivo técnico não localizado.",
                "ALTA",
            )

        if chave == "CAMADAS_TECNICAS":

            return (
                "NA",
                "Item opcional para conferência das camadas técnicas.",
                "BAIXA",
            )

        return (
            "NA",
            "Item criado automaticamente pelo pipeline técnico.",
            "MEDIA",
        )

    @staticmethod
    def gerar_checklist_inicial(
        db: Session,
        documento: DocumentoTecnico,
    ) -> None:

        if not documento:
            return

        tipo_documento = (
            DocumentoTecnicoChecklistGeneratorService
            ._normalizar_tipo_documento(documento)
        )

        if not tipo_documento:
            return

        checklist_base = (
            DocumentoTecnicoChecklistGeneratorService
            .CHECKLISTS
            .get(tipo_documento)
        )

        if not checklist_base:
            return

        try:

            for item_base in checklist_base:

                chave = str(
                    item_base["chave"]
                )

                existente = (
                    db.query(DocumentoTecnicoChecklist)
                    .filter(
                        DocumentoTecnicoChecklist.documento_tecnico_id == documento.id,

                        DocumentoTecnicoChecklist.chave == chave,
                    )
                    .first()
                )

                status_inicial, mensagem, severidade = (
                    DocumentoTecnicoChecklistGeneratorService
                    ._resolver_status_inicial(
                        documento=documento,
                        chave=chave,
                    )
                )

                if existente:

                    existente.descricao = str(
                        item_base["descricao"]
                    )

                    existente.obrigatorio = bool(
                        item_base.get(
                            "obrigatorio",
                            True,
                        )
                    )

                    existente.status = status_inicial
                    existente.mensagem = mensagem
                    existente.severidade = severidade

                    existente.validado_automaticamente = True

                    continue

                item = DocumentoTecnicoChecklist(
                    documento_tecnico_id=documento.id,

                    chave=chave,

                    descricao=str(
                        item_base["descricao"]
                    ),

                    obrigatorio=bool(
                        item_base.get(
                            "obrigatorio",
                            True,
                        )
                    ),

                    bloqueia_aprovacao=bool(
                        item_base.get(
                            "obrigatorio",
                            True,
                        )
                    ),

                    status=status_inicial,

                    etapa_validacao=tipo_documento,

                    mensagem=mensagem,

                    validado_automaticamente=True,

                    score_confianca=85,

                    severidade=severidade,
                )

                db.add(item)

            db.commit()

        except Exception:

            db.rollback()

            raise