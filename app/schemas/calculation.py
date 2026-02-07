from pydantic import BaseModel
from typing import Optional


class CalculationBase(BaseModel):
    area_hectares: float

    confrontacao_rios: bool = False
    proprietario_acompanha: bool = False
    mata_mais_50: bool = False

    finalidade: str
    partes: Optional[int] = None

    ccir_atualizado: bool = True
    itr_atualizado: bool = True
    certificado_digital: bool = True

    estaqueamento_km: float = 0.0
    notificacao_confrontantes: int = 0

    vti_imovel: Optional[float] = None


class CalculationResult(BaseModel):
    valor_base: float
    valor_variaveis_percentuais: float
    valor_variaveis_fixas: float
    valor_art: float
    valor_cartorio: float
    total_final: float


class ProposalRequest(CalculationBase):
    cliente: str
    descricao_imovel: str
    municipio: str


class ProposalResponse(BaseModel):
    sucesso: bool
    mensagem: str

    valor_base: float
    valor_art: float
    extras: float
    total: float

    html_proposta: str
    html_contrato: str
    pdf_path: str
    contract_pdf_path: str
