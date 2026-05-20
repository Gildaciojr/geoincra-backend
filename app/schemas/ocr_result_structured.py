from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


# =========================================================
# HELPERS
# =========================================================
def _texto(v: Any) -> Optional[str]:

    if v is None:
        return None

    texto = str(v).strip()

    return texto or None


# =========================================================
# QUALIDADE OCR
# =========================================================
class QualidadeOCR(BaseModel):

    score: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    erros: List[str] = []

    warnings: List[str] = []

    observacoes: List[str] = []

    inconsistencias: List[str] = []


# =========================================================
# ÁREA OCR
# =========================================================
class AreaOCR(BaseModel):

    valor: Optional[float] = None

    unidade_original: Optional[str] = None

    hectares: Optional[float] = None

    metros_quadrados: Optional[float] = None

    alqueires: Optional[float] = None


# =========================================================
# MATRÍCULA OCR
# =========================================================
class MatriculaOCR(BaseModel):

    numero: Optional[str] = None

    livro: Optional[str] = None

    folha: Optional[str] = None

    comarca: Optional[str] = None

    cartorio: Optional[str] = None

    codigo_cartorio: Optional[str] = None

    data_abertura: Optional[str] = None

    data_ultima_atualizacao: Optional[str] = None

    inteiro_teor: Optional[str] = None


# =========================================================
# PROPRIETÁRIO OCR
# =========================================================
class ProprietarioOCR(BaseModel):

    nome: str = Field(
        ...,
        min_length=3,
    )

    cpf_cnpj: Optional[str] = None

    tipo: Optional[str] = None

    rg: Optional[str] = None

    estado_civil: Optional[str] = None

    profissao: Optional[str] = None

    nacionalidade: Optional[str] = None

    endereco: Optional[str] = None

    municipio: Optional[str] = None

    estado: Optional[str] = None

    percentual_posse: Optional[str] = None

    tipo_vinculo: Optional[str] = None

    origem: Optional[str] = None


# =========================================================
# SEGMENTO OCR
# =========================================================
class SegmentoOCR(BaseModel):

    azimute_raw: Optional[str] = None

    azimute_decimal: Optional[float] = None

    distancia: float = Field(
        ...,
        gt=0,
    )

    confrontante: Optional[str] = None

    direcao: Optional[str] = None

    ordem: Optional[int] = None

    observacoes: Optional[str] = None

    @field_validator(
        "azimute_raw",
        mode="before",
    )
    @classmethod
    def resolver_azimute(
        cls,
        v,
        info,
    ):

        if v and str(v).strip():
            return str(v).strip()

        data = (
            info.data
            if hasattr(info, "data")
            else {}
        )

        return (
            data.get("azimute")
            or data.get("rumo")
            or data.get("bearing")
            or data.get("valor")
            or data.get("azimute_decimal")
        )

    @field_validator("azimute_raw")
    @classmethod
    def validar_azimute(
        cls,
        v: Optional[str],
    ) -> str:

        if not v or not str(v).strip():
            raise ValueError(
                "Azimute vazio ou não identificado"
            )

        return str(v).strip()


# =========================================================
# GEOMETRIA OCR
# =========================================================
class GeometriaOCR(BaseModel):

    fonte: Optional[str] = None

    geojson: Optional[Dict[str, Any]] = None

    segmentos: List[SegmentoOCR] = []

    memorial_texto: Optional[str] = None

    epsg: Optional[int] = None

    area_calculada: Optional[float] = None

    perimetro_calculado: Optional[float] = None

    erro_fechamento: Optional[float] = None

    referencial: Optional[str] = None

    possui_georreferenciamento_real: bool = False


# =========================================================
# IMÓVEL OCR
# =========================================================
class ImovelOCR(BaseModel):

    nome: Optional[str] = None

    descricao: Optional[str] = None

    denominacao: Optional[str] = None

    ccir: Optional[str] = None

    nirf: Optional[str] = None

    sncr: Optional[str] = None

    car: Optional[str] = None

    itr: Optional[str] = None

    municipio: Optional[str] = None

    uf: Optional[str] = None

    area: Optional[AreaOCR] = None


# =========================================================
# DOCUMENTO PESSOAL OCR
# =========================================================
class DocumentoPessoalOCR(BaseModel):

    tipo_documento: Optional[str] = None

    nome: Optional[str] = None

    cpf: Optional[str] = None

    rg: Optional[str] = None

    orgao_emissor: Optional[str] = None

    data_nascimento: Optional[str] = None

    nacionalidade: Optional[str] = None

    filiacao: List[str] = []

    naturalidade: Optional[str] = None


# =========================================================
# ATO REGISTRAL OCR
# =========================================================
class AtoRegistralOCR(BaseModel):

    tipo: Optional[str] = None

    numero: Optional[str] = None

    codigo: Optional[str] = None

    descricao: Optional[str] = None

    data: Optional[str] = None

    protocolo: Optional[str] = None

    valor: Optional[float] = None

    envolvidos: List[
        Dict[str, Optional[str]]
    ] = []

    texto_original: Optional[str] = None


# =========================================================
# HISTÓRICO OCR
# =========================================================
class HistoricoMatriculaOCR(BaseModel):

    atos: List[AtoRegistralOCR] = []

    cadeia_dominial: List[
        Dict[str, Any]
    ] = []

    matriculas_origem: List[str] = []

    matriculas_derivadas: List[str] = []

    possui_desmembramento: bool = False

    possui_remembramento: bool = False


# =========================================================
# CONFRONTANTE OCR
# =========================================================
class ConfrontanteOCR(BaseModel):

    lado: Optional[str] = None

    lado_normalizado: Optional[str] = None

    direcao: Optional[str] = None

    nome: Optional[str] = None

    descricao: Optional[str] = None

    matricula: Optional[str] = None

    identificacao: Optional[str] = None

    cpf_cnpj: Optional[str] = None

    tipo: Optional[str] = None

    lote: Optional[str] = None

    gleba: Optional[str] = None

    vinculo_registral: Optional[str] = None

    proprietarios: List[
        Dict[str, Any]
    ] = []

    matricula_relacionada: Optional[
        Dict[str, Any]
    ] = None


# =========================================================
# DADOS SIG
# =========================================================
class DadosSIGOCR(BaseModel):

    codigo_imovel: Optional[str] = None

    sistema_origem: Optional[str] = None

    responsavel_tecnico: Optional[str] = None

    codigo_profissional: Optional[str] = None

    art: Optional[str] = None

    certificacao_sigef: Optional[str] = None

    status_sigef: Optional[str] = None


# =========================================================
# CROQUI OCR
# =========================================================
class CroquiOCR(BaseModel):

    descricao: Optional[str] = None

    possui_vertices: bool = False

    possui_medidas: bool = False

    possui_confrontantes: bool = False

    observacoes: Optional[str] = None


# =========================================================
# PIPELINE OCR
# =========================================================
class PipelineOCRMetadata(BaseModel):

    pipeline: Optional[str] = None

    engine: Optional[str] = None

    modelo_llm: Optional[str] = None

    parser_service: Optional[str] = None

    normalizer_service: Optional[str] = None

    post_processor_service: Optional[str] = None

    versao_pipeline: Optional[int] = None

    tempo_processamento_ms: Optional[int] = None


# =========================================================
# ROOT OCR
# =========================================================
class OCRStructured(BaseModel):

    # =====================================================
    # PIPELINE
    # =====================================================
    metadata_pipeline: Optional[
        PipelineOCRMetadata
    ] = None

    # =====================================================
    # MATRÍCULA
    # =====================================================
    matricula: Optional[
        MatriculaOCR
    ] = None

    # =====================================================
    # IMÓVEL
    # =====================================================
    imovel: Optional[
        ImovelOCR
    ] = None

    # =====================================================
    # PROPRIETÁRIOS
    # =====================================================
    proprietarios: List[
        ProprietarioOCR
    ] = []

    # =====================================================
    # GEOMETRIA
    # =====================================================
    geometria: Optional[
        GeometriaOCR
    ] = None

    # =====================================================
    # CONFRONTANTES
    # =====================================================
    confrontantes: List[
        ConfrontanteOCR
    ] = []

    # =====================================================
    # HISTÓRICO REGISTRAL
    # =====================================================
    historico: Optional[
        HistoricoMatriculaOCR
    ] = None

    # =====================================================
    # DOCUMENTOS PESSOAIS
    # =====================================================
    documentos_pessoais: List[
        DocumentoPessoalOCR
    ] = []

    # =====================================================
    # SIG / CADASTRAL
    # =====================================================
    dados_sig: Optional[
        DadosSIGOCR
    ] = None

    # =====================================================
    # CROQUI
    # =====================================================
    croqui: Optional[
        CroquiOCR
    ] = None

    # =====================================================
    # DADOS BRUTOS
    # =====================================================
    dados_brutos: Optional[
        Dict[str, Any]
    ] = None

    # =====================================================
    # QUALIDADE
    # =====================================================
    qualidade: QualidadeOCR

    # =====================================================
    # VALIDADORES
    # =====================================================
    @field_validator(
        "proprietarios",
        mode="after",
    )
    @classmethod
    def validar_proprietarios(
        cls,
        v,
    ):

        if not isinstance(v, list):
            raise ValueError(
                "Lista de proprietários inválida"
            )

        return v

    @field_validator(
        "confrontantes",
        mode="after",
    )
    @classmethod
    def validar_confrontantes(
        cls,
        v,
    ):

        if not isinstance(v, list):
            raise ValueError(
                "Lista de confrontantes inválida"
            )

        return v