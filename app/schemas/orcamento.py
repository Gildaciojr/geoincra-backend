from pydantic import BaseModel
from typing import Optional


class OrcamentoRequest(BaseModel):
    # 🔹 DADOS DO CLIENTE
    cliente: str
    municipio: str
    descricao_imovel: str

    # 🔹 CAMPOS DE CÁLCULO (HERDADOS)
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

    # 🔹 OPCIONAL FUTURO
    project_id: Optional[int] = None