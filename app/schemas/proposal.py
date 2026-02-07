# app/schemas/proposal.py

from pydantic import BaseModel

class ProposalRequestSchema(BaseModel):
    client_name: str
    client_cpf: str
    project_name: str
    area_hectares: float
    price_per_hectare: float
    minimum_value: float
    final_value: float
    description: str | None = ""
