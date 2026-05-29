from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.documento_tecnico_crud import create_documento_tecnico
from app.models.automation_job import AutomationJob
from app.models.automation_result import AutomationResult
from app.models.confrontante import Confrontante
from app.models.geometria import Geometria
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.models.proprietario import Proprietario
from app.schemas.documento_tecnico import DocumentoTecnicoCreate


class FichaCadastralSigRiService:
    DOCUMENT_GROUP_KEY = "FICHA_CADASTRAL_SIG_RI"
    TIPO_DOCUMENTO = "Ficha Cadastral SIG-RI"

    @staticmethod
    def _extrair_regex(texto: Optional[str], padrao: str) -> Optional[str]:
        if not texto:
            return None

        match = re.search(padrao, texto, flags=re.IGNORECASE)

        if not match:
            return None

        return str(match.group(1)).strip()

    @staticmethod
    def _formatar_float(valor: Optional[float], casas: int = 4) -> Optional[float]:
        if valor is None:
            return None

        try:
            return round(float(valor), casas)
        except Exception:
            return None

    @staticmethod
    def _buscar_geometria_principal(db: Session, imovel_id: int) -> Geometria | None:
        return (
            db.query(Geometria)
            .filter(Geometria.imovel_id == imovel_id)
            .order_by(Geometria.id.desc())
            .first()
        )

    @staticmethod
    def _buscar_matricula_principal(db: Session, imovel: Imovel) -> Matricula | None:
        query = db.query(Matricula).filter(Matricula.imovel_id == imovel.id)

        if imovel.matricula_principal:
            encontrada = (
                query
                .filter(Matricula.numero_matricula == imovel.matricula_principal)
                .first()
            )

            if encontrada:
                return encontrada

        return query.order_by(Matricula.id.desc()).first()

    @staticmethod
    def _buscar_proprietario_principal(db: Session, imovel_id: int) -> Proprietario | None:
        return (
            db.query(Proprietario)
            .filter(Proprietario.imovel_id == imovel_id)
            .order_by(Proprietario.id.asc())
            .first()
        )

    @staticmethod
    def _listar_confrontantes(db: Session, imovel_id: int) -> list[Confrontante]:
        return (
            db.query(Confrontante)
            .filter(Confrontante.imovel_id == imovel_id)
            .order_by(
                Confrontante.ordem_segmento.asc().nullslast(),
                Confrontante.id.asc(),
            )
            .all()
        )

    @staticmethod
    def _buscar_resultado_automacao_mais_recente(
        db: Session,
        project_id: int,
    ) -> AutomationResult | None:
        return (
            db.query(AutomationResult)
            .join(AutomationJob, AutomationResult.job_id == AutomationJob.id)
            .filter(AutomationJob.project_id == project_id)
            .order_by(AutomationResult.created_at.desc())
            .first()
        )

    @staticmethod
    def montar_payload(db: Session, imovel_id: int) -> dict[str, object]:
        imovel = db.get(Imovel, imovel_id)

        if not imovel:
            raise ValueError("Imóvel não encontrado.")

        project = imovel.project

        geometria = FichaCadastralSigRiService._buscar_geometria_principal(
            db=db,
            imovel_id=imovel.id,
        )

        matricula = FichaCadastralSigRiService._buscar_matricula_principal(
            db=db,
            imovel=imovel,
        )

        proprietario = FichaCadastralSigRiService._buscar_proprietario_principal(
            db=db,
            imovel_id=imovel.id,
        )

        confrontantes = FichaCadastralSigRiService._listar_confrontantes(
            db=db,
            imovel_id=imovel.id,
        )

        resultado_automacao = None

        if project:
            resultado_automacao = (
                FichaCadastralSigRiService
                ._buscar_resultado_automacao_mais_recente(
                    db=db,
                    project_id=project.id,
                )
            )

        metadata_automacao = (
            resultado_automacao.metadata_json
            if resultado_automacao and isinstance(resultado_automacao.metadata_json, dict)
            else {}
        )

        municipio = imovel.municipio

        inteiro_teor = matricula.inteiro_teor if matricula else None

        area_ha = (
            geometria.area_hectares
            if geometria and geometria.area_hectares is not None
            else imovel.area_hectares
        )

        area_m2 = area_ha * 10000 if area_ha is not None else None

        perimetro_m = geometria.perimetro_m if geometria else None
        perimetro_km = perimetro_m / 1000 if perimetro_m is not None else None

        cnm = (
            resultado_automacao.cnm
            if resultado_automacao and resultado_automacao.cnm
            else FichaCadastralSigRiService._extrair_regex(
                inteiro_teor,
                r"\bCNM\b[:\s\-]*([0-9.\-]+)",
            )
        )

        protocolo = (
            resultado_automacao.protocolo
            if resultado_automacao and resultado_automacao.protocolo
            else FichaCadastralSigRiService._extrair_regex(
                inteiro_teor,
                r"\bprotocolo\b[:\s\-]*([0-9.\-/]+)",
            )
        )

        codigo_sigef = (
            getattr(project, "codigo_sigef", None)
            or metadata_automacao.get("codigo_sigef")
        )

        codigo_car = getattr(project, "codigo_car", None)
        codigo_sncr = getattr(project, "codigo_sncr", None)

        ccir_sncr = (
            imovel.ccir
            or codigo_sncr
            or metadata_automacao.get("ccir_sncr")
        )

        confrontantes_payload: list[dict[str, object | None]] = []

        for confrontante in confrontantes:
            confrontantes_payload.append(
                {
                    "direcao": confrontante.direcao,
                    "direcao_normalizada": confrontante.direcao_normalizada,
                    "ordem_segmento": confrontante.ordem_segmento,
                    "nome": confrontante.nome_confrontante,
                    "matricula": confrontante.matricula_confrontante,
                    "identificacao_imovel": (
                        confrontante.identificacao_imovel_confrontante
                    ),
                    "descricao": confrontante.descricao,
                    "tipo": confrontante.tipo,
                    "lote": confrontante.lote,
                    "gleba": confrontante.gleba,
                }
            )

        payload: dict[str, object] = {
            "identificacao_imovel": {
                "nome_imovel": imovel.nome or metadata_automacao.get("nome_area"),
                "nome_propriedade": imovel.nome or metadata_automacao.get("nome_area"),
                "tipo_imovel": "Rural",
            },
            "proprietario": {
                "nome": proprietario.nome_completo if proprietario else None,
                "cpf": proprietario.cpf if proprietario else None,
                "cnpj": proprietario.cnpj if proprietario else None,
            },
            "cadastros_registros": {
                "matricula": (
                    matricula.numero_matricula
                    if matricula
                    else (
                        resultado_automacao.matricula
                        if resultado_automacao
                        else imovel.matricula_principal
                    )
                ),
                "cnm": cnm,
                "ccir_sncr": ccir_sncr,
                "snci_codigo_imovel_rural": imovel.codigo_incra or codigo_sncr,
                "cib_nirf": imovel.nirf,
                "itr": imovel.itr,
                "car": codigo_car,
                "sigef": codigo_sigef,
            },
            "localizacao": {
                "endereco_localidade": imovel.descricao,
                "cep": proprietario.cep if proprietario else None,
                "cidade": (
                    municipio.nome
                    if municipio
                    else (
                        getattr(project, "municipio", None)
                        if project
                        else metadata_automacao.get("municipio")
                    )
                ),
                "uf": (
                    municipio.estado
                    if municipio
                    else (
                        getattr(project, "uf", None)
                        if project
                        else metadata_automacao.get("uf")
                    )
                ),
            },
            "medidas_confrontacoes": {
                "area_m2": FichaCadastralSigRiService._formatar_float(area_m2, 2),
                "area_ha": FichaCadastralSigRiService._formatar_float(area_ha, 4),
                "perimetro_m": (
                    FichaCadastralSigRiService._formatar_float(perimetro_m, 2)
                ),
                "perimetro_km": (
                    FichaCadastralSigRiService._formatar_float(perimetro_km, 4)
                ),
                "confrontantes": confrontantes_payload,
                "nomes_confrontantes": [
                    item["nome"]
                    for item in confrontantes_payload
                    if item.get("nome")
                ],
                "matriculas_confrontantes": [
                    item["matricula"]
                    for item in confrontantes_payload
                    if item.get("matricula")
                ],
            },
            "protocolo_cartorio": {
                "prenotacao_protocolo": protocolo,
            },
            "metadata": {
                "gerado_em": datetime.utcnow().isoformat(),
                "fonte": "GEOINCRA",
                "documento": "Ficha Cadastral de Imóvel no SIG-RI",
                "imovel_id": imovel.id,
                "project_id": project.id if project else None,
                "matricula_id": matricula.id if matricula else None,
                "geometria_id": geometria.id if geometria else None,
                "automation_result_id": (
                    str(resultado_automacao.id)
                    if resultado_automacao
                    else None
                ),
                "total_confrontantes": len(confrontantes_payload),
            },
        }

        return payload

    @staticmethod
    def renderizar_texto(payload: dict[str, object]) -> str:
        identificacao = payload.get("identificacao_imovel", {})
        proprietario = payload.get("proprietario", {})
        cadastros = payload.get("cadastros_registros", {})
        localizacao = payload.get("localizacao", {})
        medidas = payload.get("medidas_confrontacoes", {})
        protocolo = payload.get("protocolo_cartorio", {})

        confrontantes = (
            medidas.get("confrontantes", [])
            if isinstance(medidas, dict)
            else []
        )

        linhas: list[str] = []

        linhas.append("Ficha Cadastral Simplificada")
        linhas.append("")
        linhas.append("1. Identificação do Imóvel")
        linhas.append(f"Nome do Imóvel: {identificacao.get('nome_imovel') or ''}")
        linhas.append(
            f"Nome da Propriedade: "
            f"{identificacao.get('nome_propriedade') or ''}"
        )
        linhas.append("Tipo do Imóvel: Rural")
        linhas.append("")

        linhas.append("2. Dados do Proprietário")
        linhas.append(f"Nome do Proprietário: {proprietario.get('nome') or ''}")
        linhas.append(
            f"CPF/CNPJ: "
            f"{proprietario.get('cpf') or proprietario.get('cnpj') or ''}"
        )
        linhas.append("")

        linhas.append("3. Cadastros e Registros")
        linhas.append(f"Matrícula: {cadastros.get('matricula') or ''}")
        linhas.append(f"CNM: {cadastros.get('cnm') or ''}")
        linhas.append(
            f"CCIR / SNCR (INCRA): {cadastros.get('ccir_sncr') or ''}"
        )
        linhas.append(
            f"SNCI (Código CCIR): "
            f"{cadastros.get('snci_codigo_imovel_rural') or ''}"
        )
        linhas.append(
            f"CIB / NIRF (Receita Federal): {cadastros.get('cib_nirf') or ''}"
        )
        linhas.append(f"CAR (Cadastro Ambiental): {cadastros.get('car') or ''}")
        linhas.append(
            f"SIGEF (Georreferenciamento): {cadastros.get('sigef') or ''}"
        )
        linhas.append("")

        linhas.append("4. Localização")
        linhas.append(
            f"Endereço / Localidade: "
            f"{localizacao.get('endereco_localidade') or ''}"
        )
        linhas.append(f"CEP: {localizacao.get('cep') or ''}")
        linhas.append(f"Cidade: {localizacao.get('cidade') or ''}")
        linhas.append(f"UF: {localizacao.get('uf') or ''}")
        linhas.append("")

        linhas.append("5. Medidas e Confrontações")
        linhas.append(f"Área (m²): {medidas.get('area_m2') or ''}")
        linhas.append(f"Área (ha): {medidas.get('area_ha') or ''}")
        linhas.append(f"Perímetro (m): {medidas.get('perimetro_m') or ''}")
        linhas.append(f"Perímetro (km): {medidas.get('perimetro_km') or ''}")
        linhas.append("")
        linhas.append("Nome dos Confrontantes:")

        if isinstance(confrontantes, list):
            for item in confrontantes:
                if not isinstance(item, dict):
                    continue

                nome = item.get("nome")
                direcao = item.get("direcao")
                descricao = item.get("descricao")

                if nome:
                    linhas.append(f"- {direcao or ''}: {nome}")
                elif descricao:
                    linhas.append(f"- {direcao or ''}: {descricao}")

        linhas.append("")
        linhas.append("Confrontantes (Matrículas):")

        if isinstance(confrontantes, list):
            for item in confrontantes:
                if not isinstance(item, dict):
                    continue

                matricula = item.get("matricula")
                direcao = item.get("direcao")

                if matricula:
                    linhas.append(f"- {direcao or ''}: {matricula}")

        linhas.append("")
        linhas.append("6. Protocolo Cartório")
        linhas.append(
            f"Prenotação / Protocolo: "
            f"{protocolo.get('prenotacao_protocolo') or ''}"
        )

        return "\n".join(linhas)

    @staticmethod
    def gerar_documento_tecnico(
        db: Session,
        imovel_id: int,
        observacoes_tecnicas: Optional[str] = None,
    ):
        payload = FichaCadastralSigRiService.montar_payload(
            db=db,
            imovel_id=imovel_id,
        )

        texto = FichaCadastralSigRiService.renderizar_texto(payload)

        return create_documento_tecnico(
            db=db,
            imovel_id=imovel_id,
            data=DocumentoTecnicoCreate(
                document_group_key=FichaCadastralSigRiService.DOCUMENT_GROUP_KEY,
                tipo=FichaCadastralSigRiService.TIPO_DOCUMENTO,
                status_tecnico="EM_ANALISE",
                observacoes_tecnicas=observacoes_tecnicas,
                conteudo_texto=texto,
                conteudo_json=payload,
                arquivo_path=None,
                metadata_json={
                    "tipo": FichaCadastralSigRiService.TIPO_DOCUMENTO,
                    "document_group_key": (
                        FichaCadastralSigRiService.DOCUMENT_GROUP_KEY
                    ),
                    "gerado_em": datetime.utcnow().isoformat(),
                    "origem": "consolidacao_sig_ri",
                },
                gerado_em=datetime.utcnow(),
            ),
        )