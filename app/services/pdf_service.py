from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# 🔥 NOVO
from weasyprint import HTML


# =========================================================
# BASE PATHS
# =========================================================
DOCKER_BASE = Path("/app/app/uploads")
LOCAL_BASE = Path("app/uploads")


def _resolve_base() -> Path:
    if DOCKER_BASE.exists():
        return DOCKER_BASE
    return LOCAL_BASE


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


# =========================================================
# (mantido, mas NÃO usado mais)
# =========================================================
def _limpar_html_simples(html: str) -> list[str]:
    substituicoes = {
        "<br>": "\n",
        "<br />": "\n",
        "<hr />": "-" * 60,
        "<h1>": "",
        "</h1>": "",
        "<h3>": "",
        "</h3>": "",
        "<p>": "",
        "</p>": "",
        "<b>": "",
        "</b>": "",
        "<li>": " - ",
        "</li>": "",
        "<ul>": "",
        "</ul>": "",
    }

    texto = html
    for k, v in substituicoes.items():
        texto = texto.replace(k, v)

    return texto.split("\n")


# =========================================================
# 📄 ORÇAMENTO (PROFISSIONAL - HTML + WEASYPRINT)
# =========================================================
def gerar_pdf_orcamento(
    project_id: int | None,
    calculation,
    cliente: str = "",
    municipio: str = "",
    descricao: str = "",
) -> str:

    base_root = _resolve_base()
    base = base_root / "orcamentos" / f"project_{project_id or 'preview'}"
    _ensure_dir(base)

    filename = f"orcamento_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = base / filename

    # =========================================================
    # HTML PROFISSIONAL
    # =========================================================
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                color: #1e293b;
            }}

            h1 {{
                text-align: center;
                font-size: 22px;
                margin-bottom: 20px;
            }}

            h2 {{
                font-size: 14px;
                margin-top: 20px;
                border-bottom: 1px solid #cbd5e1;
                padding-bottom: 4px;
            }}

            .box {{
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 12px;
                margin-top: 10px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                font-size: 12px;
            }}

            .total {{
                font-size: 20px;
                font-weight: bold;
                color: #059669;
                margin-top: 10px;
            }}

            .footer {{
                margin-top: 40px;
                font-size: 10px;
                color: #64748b;
                text-align: center;
            }}
        </style>
    </head>

    <body>

        <h1>ORÇAMENTO TÉCNICO</h1>

        <div class="box">
            <div class="grid">
                <div><b>Cliente:</b> {cliente or "-"}</div>
                <div><b>Município:</b> {municipio or "-"}</div>
                <div><b>Imóvel:</b> {descricao or "-"}</div>
                <div><b>Data:</b> {datetime.utcnow().strftime("%d/%m/%Y")}</div>
            </div>
        </div>

        <h2>Composição de Custos</h2>

        <div class="box">
            <p>Valor base: R$ {calculation.valor_base:.2f}</p>
            <p>Custos adicionais: R$ {(calculation.valor_variaveis_fixas + calculation.valor_variaveis_percentuais):.2f}</p>
            <p>ART: R$ {calculation.valor_art:.2f}</p>
            <p>Cartório: R$ {calculation.valor_cartorio:.2f}</p>
        </div>

        <div class="box total">
            TOTAL: R$ {calculation.total_final:.2f}
        </div>

        <div class="footer">
            Documento gerado automaticamente pelo sistema GeoINCRA<br/>
            Este orçamento não constitui contrato<br/>
            Validade: 60 dias
        </div>

    </body>
    </html>
    """

    # =========================================================
    # GERAÇÃO DO PDF
    # =========================================================
    HTML(string=html).write_pdf(str(file_path))

    # 🔥 RETORNO PADRÃO DO SISTEMA (IMPORTANTE)
    return str(file_path.relative_to(base_root))


# =========================================================
# 📄 PROPOSTA (AGORA CORRETA)
# =========================================================
def gerar_pdf_proposta(project_id: int, html_simples: str) -> str:
    base_root = _resolve_base()
    base = base_root / "propostas" / f"project_{project_id}"
    _ensure_dir(base)

    filename = f"proposta_project_{project_id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = base / filename

    # 🔥 HTML REAL → PDF REAL
    HTML(string=html_simples).write_pdf(str(file_path))

    return str(file_path.relative_to(base_root))


# =========================================================
# 📄 CONTRATO (AGORA CORRETO)
# =========================================================
def gerar_pdf_contrato(project_id: int, html_simples: str) -> str:
    base_root = _resolve_base()
    base = base_root / "propostas" / f"project_{project_id}"
    _ensure_dir(base)

    filename = f"contrato_project_{project_id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = base / filename

    HTML(string=html_simples).write_pdf(str(file_path))

    return str(file_path.relative_to(base_root))


# =========================================================
# 📄 PDF TÉCNICO COMPLETO (CROQUI + MEMORIAL)
# =========================================================
def gerar_pdf_imovel(
    imovel_id: int,
    nome_imovel: str,
    area_ha: float,
    perimetro_m: float,
    memorial_texto: str,
    croqui_svg: str,
) -> str:

    base_root = _resolve_base()
    base = base_root / "imoveis" / f"{imovel_id}" / "pdfs"
    _ensure_dir(base)

    filename = f"imovel_{imovel_id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = base / filename

    # =========================================================
    # HTML PROFISSIONAL
    # =========================================================
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                color: #1e293b;
            }}

            h1 {{
                font-size: 22px;
                text-align: center;
                margin-bottom: 10px;
            }}

            h2 {{
                font-size: 16px;
                margin-top: 30px;
                border-bottom: 1px solid #cbd5e1;
                padding-bottom: 4px;
            }}

            .box {{
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 12px;
                margin-top: 10px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                font-size: 12px;
            }}

            .label {{
                color: #64748b;
            }}

            .value {{
                font-weight: bold;
            }}

            .memorial {{
                white-space: pre-wrap;
                font-size: 12px;
                line-height: 1.5;
            }}

            .footer {{
                margin-top: 40px;
                font-size: 10px;
                color: #64748b;
                text-align: center;
            }}

            svg {{
                width: 100%;
                height: auto;
            }}
        </style>
    </head>

    <body>

        <h1>DOCUMENTAÇÃO TÉCNICA DO IMÓVEL</h1>

        <div class="box">
            <div class="grid">
                <div><span class="label">Imóvel:</span> <span class="value">{nome_imovel}</span></div>
                <div><span class="label">Área (ha):</span> <span class="value">{area_ha:.4f}</span></div>
                <div><span class="label">Perímetro (m):</span> <span class="value">{perimetro_m:.3f}</span></div>
                <div><span class="label">Data:</span> <span class="value">{datetime.utcnow().strftime("%d/%m/%Y")}</span></div>
            </div>
        </div>

        <h2>CROQUI DO IMÓVEL</h2>

        <div class="box">
            {croqui_svg}
        </div>

        <h2>MEMORIAL DESCRITIVO</h2>

        <div class="box memorial">
            {memorial_texto}
        </div>

        <div class="footer">
            Documento gerado automaticamente pelo sistema GeoINCRA<br/>
            Pipeline: OCR + IA + Geometria + Engenharia de Documentos
        </div>

    </body>
    </html>
    """

    # =========================================================
    # GERAÇÃO DO PDF
    # =========================================================
    HTML(string=html).write_pdf(str(file_path))

    return str(file_path.relative_to(base_root))