# geoincra_backend/app/services/proposal_service.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.models.municipio import Municipio
from app.schemas.calculation import ProposalRequest
from app.services.calculation_service import CalculationService
from app.services.pdf_service import gerar_pdf_proposta, gerar_pdf_contrato


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _obter_vti_imovel_por_municipio(
    db: Session,
    municipio_nome: str | None,
    area_ha: float | None,
) -> float | None:
    if not municipio_nome or not area_ha or area_ha <= 0:
        return None

    municipio = (
        db.query(Municipio)
        .filter(Municipio.nome.ilike(municipio_nome))
        .first()
    )
    if not municipio:
        return None

    base_ha = max(municipio.vti_min or 0, municipio.vtn_min or 0)
    return base_ha * area_ha if base_ha > 0 else None


def generate_full_proposal(
    db: Session,
    payload: ProposalRequest,
    project_id: int,
    user_id: int,  # reservado para auditoria futura
) -> dict:
    # 1) VTI garantido
    vti_imovel = payload.vti_imovel
    if vti_imovel is None:
        vti_imovel = _obter_vti_imovel_por_municipio(
            db=db,
            municipio_nome=payload.municipio,
            area_ha=payload.area_hectares,
        )

    # 2) payload com vti garantido
    try:
        calc_req = payload.model_copy(update={"vti_imovel": vti_imovel})
    except AttributeError:
        calc_req = payload.copy(update={"vti_imovel": vti_imovel})

    # 3) cálculo central
    resultado = CalculationService.calcular(db, calc_req)

    # 4) breakdown adicional (cartório/itbi/art)
    cart = CalculationService.calcular_cartorio(db, vti_imovel)
    qtd_arts, valor_art_total = CalculationService.calcular_art(db, payload.finalidade)

    extras = float(resultado.valor_variaveis_percentuais) + float(resultado.valor_variaveis_fixas)

    dados = {
        "valor_base": float(resultado.valor_base),
        "valor_variaveis_percentuais": float(resultado.valor_variaveis_percentuais),
        "valor_variaveis_fixas": float(resultado.valor_variaveis_fixas),
        "extras": float(extras),

        "qtd_arts": int(qtd_arts),
        "valor_art": float(valor_art_total),

        "valor_cartorio": float(cart["total"]),
        "cartorio_breakdown": cart,   # escritura/registro/certidão/itbi/percent

        "total": float(resultado.total_final),
        "vti_imovel": float(vti_imovel) if vti_imovel else None,
    }

    # 5) render templates HTML oficiais
    data_atual = datetime.now().strftime("%d/%m/%Y")

    # (logo_path) - você pode apontar para um arquivo real depois
    logo_path = ""

    proposta_tpl = env.get_template("proposal_template.html")
    contrato_tpl = env.get_template("contract_template.html")

    html_proposta = proposta_tpl.render(
        data_atual=data_atual,
        logo_path=logo_path,
        cliente=payload.cliente,
        descricao_imovel=payload.descricao_imovel,
        municipio=payload.municipio,
        area=float(payload.area_hectares),

        valor_base=dados["valor_base"],
        extras=dados["extras"],
        total=dados["total"],
        valor_art=dados["valor_art"],
        arts=dados["qtd_arts"],

        # cartório
        valor_cartorio=dados["valor_cartorio"],
        escritura=cart["escritura"],
        registro=cart["registro"],
        certidao_onus_reais=cart["certidao_onus_reais"],
        itbi=cart["itbi"],
        itbi_percentual=cart["itbi_percentual"],
        vti_imovel=dados["vti_imovel"],
    )

    html_contrato = contrato_tpl.render(
        data_atual=data_atual,
        logo_path=logo_path,
        cliente=payload.cliente,
        descricao_imovel=payload.descricao_imovel,
        municipio=payload.municipio,

        valor_base=dados["valor_base"],
        extras=dados["extras"],
        total=dados["total"],
        valor_art=dados["valor_art"],
        arts=dados["qtd_arts"],

        valor_cartorio=dados["valor_cartorio"],
        escritura=cart["escritura"],
        registro=cart["registro"],
        certidao_onus_reais=cart["certidao_onus_reais"],
        itbi=cart["itbi"],
        itbi_percentual=cart["itbi_percentual"],
        vti_imovel=dados["vti_imovel"],
    )

    # 6) PDFs
    pdf_proposta_path = gerar_pdf_proposta(project_id=project_id, html_simples=html_proposta)
    pdf_contrato_path = gerar_pdf_contrato(project_id=project_id, html_simples=html_contrato)

    return {
        "dados": dados,  # ✅ frontend (BudgetWizard) usa result.dados.*
        "html_proposta": html_proposta,
        "html_contrato": html_contrato,
        "pdf_proposta": pdf_proposta_path,
        "pdf_contrato": pdf_contrato_path,
    }
