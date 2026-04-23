from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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
# HELPERS VISUAIS
# =========================================================
def _brl(valor: float) -> str:
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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

    valor_base = float(calculation.valor_base or 0)
    valor_extras = float(
        (calculation.valor_variaveis_fixas or 0)
        + (calculation.valor_variaveis_percentuais or 0)
    )
    valor_art = float(calculation.valor_art or 0)
    valor_cartorio = float(calculation.valor_cartorio or 0)
    valor_total = float(calculation.total_final or 0)

    data_geracao = datetime.utcnow().strftime("%d/%m/%Y")

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 20mm 16mm 18mm 16mm;
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                color: #0f172a;
                margin: 0;
                padding: 0;
                background: #ffffff;
            }}

            .page {{
                width: 100%;
            }}

            .hero {{
                background: linear-gradient(135deg, #047857 0%, #059669 45%, #0f766e 100%);
                color: #ffffff;
                border-radius: 18px;
                padding: 28px 30px 26px 30px;
                box-shadow: 0 18px 45px rgba(5, 150, 105, 0.18);
            }}

            .hero-top {{
                display: table;
                width: 100%;
            }}

            .hero-left,
            .hero-right {{
                display: table-cell;
                vertical-align: top;
            }}

            .hero-right {{
                text-align: right;
                width: 180px;
            }}

            .brand-badge {{
                display: inline-block;
                padding: 7px 12px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.18);
                font-size: 11px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                font-weight: bold;
            }}

            .hero h1 {{
                margin: 16px 0 8px 0;
                font-size: 30px;
                line-height: 1.1;
                letter-spacing: 0.02em;
            }}

            .hero p {{
                margin: 0;
                font-size: 13px;
                line-height: 1.5;
                color: rgba(255, 255, 255, 0.92);
            }}

            .hero-date {{
                margin-top: 10px;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.95);
            }}

            .content {{
                margin-top: 18px;
            }}

            .section-title {{
                font-size: 18px;
                font-weight: bold;
                color: #065f46;
                margin: 0 0 10px 0;
            }}

            .section-subtitle {{
                font-size: 12px;
                color: #475569;
                margin: 0 0 18px 0;
            }}

            .info-grid {{
                display: table;
                width: 100%;
                border-spacing: 0 12px;
            }}

            .info-row {{
                display: table-row;
            }}

            .info-card {{
                display: table-cell;
                width: 50%;
                padding: 0 6px;
                vertical-align: top;
            }}

            .card {{
                background: #ffffff;
                border: 1px solid #dbeafe;
                border-radius: 16px;
                padding: 16px 18px;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            }}

            .card.soft-emerald {{
                border: 1px solid #bbf7d0;
                background: linear-gradient(180deg, #ffffff 0%, #f0fdf4 100%);
            }}

            .card.soft-teal {{
                border: 1px solid #99f6e4;
                background: linear-gradient(180deg, #ffffff 0%, #f0fdfa 100%);
            }}

            .label {{
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 8px;
            }}

            .value {{
                font-size: 18px;
                font-weight: bold;
                color: #0f172a;
                line-height: 1.3;
            }}

            .value.small {{
                font-size: 15px;
                font-weight: 600;
            }}

            .costs {{
                margin-top: 10px;
                border: 1px solid #d1fae5;
                border-radius: 18px;
                overflow: hidden;
                box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            }}

            .costs-header {{
                background: linear-gradient(90deg, #ecfdf5 0%, #f0fdfa 100%);
                padding: 16px 20px;
                border-bottom: 1px solid #d1fae5;
            }}

            .costs-header h2 {{
                margin: 0;
                font-size: 19px;
                color: #065f46;
            }}

            .costs-header p {{
                margin: 5px 0 0 0;
                font-size: 12px;
                color: #64748b;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            .cost-table td {{
                padding: 15px 20px;
                font-size: 14px;
                border-bottom: 1px solid #ecfdf5;
            }}

            .cost-table tr:last-child td {{
                border-bottom: none;
            }}

            .cost-table td:first-child {{
                color: #334155;
                font-weight: 600;
            }}

            .cost-table td:last-child {{
                text-align: right;
                font-weight: bold;
                color: #0f172a;
                white-space: nowrap;
            }}

            .total-box {{
                margin-top: 18px;
                background: linear-gradient(135deg, #064e3b 0%, #047857 45%, #0f766e 100%);
                color: #ffffff;
                border-radius: 20px;
                padding: 22px 24px;
                box-shadow: 0 20px 45px rgba(4, 120, 87, 0.18);
            }}

            .total-grid {{
                display: table;
                width: 100%;
            }}

            .total-left,
            .total-right {{
                display: table-cell;
                vertical-align: middle;
            }}

            .total-right {{
                text-align: right;
                width: 240px;
            }}

            .total-caption {{
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.10em;
                font-weight: bold;
                color: rgba(255, 255, 255, 0.8);
            }}

            .total-title {{
                margin-top: 8px;
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 0.02em;
            }}

            .total-note {{
                margin-top: 6px;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.86);
            }}

            .total-value {{
                font-size: 34px;
                font-weight: bold;
                line-height: 1;
                letter-spacing: 0.01em;
            }}

            .legal-box {{
                margin-top: 18px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                padding: 16px 18px;
            }}

            .legal-box h3 {{
                margin: 0 0 8px 0;
                font-size: 14px;
                color: #0f172a;
            }}

            .legal-box p {{
                margin: 0;
                font-size: 12px;
                color: #475569;
                line-height: 1.6;
            }}

            .footer {{
                margin-top: 28px;
                text-align: center;
                font-size: 11px;
                color: #64748b;
                line-height: 1.5;
            }}

            .footer strong {{
                color: #0f172a;
            }}
        </style>
    </head>

    <body>
        <div class="page">

            <div class="hero">
                <div class="hero-top">
                    <div class="hero-left">
                        <span class="brand-badge">Portal GeoINCRA</span>
                        <h1>Orçamento Técnico</h1>
                        <p>
                            Documento gerado automaticamente para apoio comercial e análise
                            técnica preliminar do serviço solicitado.
                        </p>
                    </div>

                    <div class="hero-right">
                        <div class="hero-date">
                            <strong>Data de emissão</strong><br/>
                            {data_geracao}
                        </div>
                    </div>
                </div>
            </div>

            <div class="content">
                <p class="section-title">Dados principais</p>
                <p class="section-subtitle">
                    Informações utilizadas para composição e apresentação do orçamento.
                </p>

                <div class="info-grid">
                    <div class="info-row">
                        <div class="info-card">
                            <div class="card soft-emerald">
                                <div class="label">Cliente</div>
                                <div class="value">{cliente or "-"}</div>
                            </div>
                        </div>

                        <div class="info-card">
                            <div class="card soft-teal">
                                <div class="label">Município</div>
                                <div class="value">{municipio or "-"}</div>
                            </div>
                        </div>
                    </div>

                    <div class="info-row">
                        <div class="info-card">
                            <div class="card">
                                <div class="label">Imóvel / referência</div>
                                <div class="value small">{descricao or "-"}</div>
                            </div>
                        </div>

                        <div class="info-card">
                            <div class="card">
                                <div class="label">Projeto</div>
                                <div class="value">{project_id if project_id else "Preview"}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="costs">
                    <div class="costs-header">
                        <h2>Composição de custos</h2>
                        <p>
                            Estrutura consolidada com base no motor de cálculo do sistema.
                        </p>
                    </div>

                    <table class="cost-table">
                        <tr>
                            <td>Valor base do serviço</td>
                            <td>R$ {_brl(valor_base)}</td>
                        </tr>
                        <tr>
                            <td>Custos adicionais e variáveis</td>
                            <td>R$ {_brl(valor_extras)}</td>
                        </tr>
                        <tr>
                            <td>ART</td>
                            <td>R$ {_brl(valor_art)}</td>
                        </tr>
                        <tr>
                            <td>Cartório</td>
                            <td>R$ {_brl(valor_cartorio)}</td>
                        </tr>
                    </table>
                </div>

                <div class="total-box">
                    <div class="total-grid">
                        <div class="total-left">
                            <div class="total-caption">Valor consolidado</div>
                            <div class="total-title">Total do orçamento</div>
                            <div class="total-note">
                                Estimativa calculada conforme parâmetros técnicos e operacionais informados.
                            </div>
                        </div>

                        <div class="total-right">
                            <div class="total-value">R$ {_brl(valor_total)}</div>
                        </div>
                    </div>
                </div>

                <div class="legal-box">
                    <h3>Observações importantes</h3>
                    <p>
                        Este orçamento possui caráter estimativo e não constitui contrato definitivo.
                        Sua validade é de <strong>60 dias</strong>, podendo sofrer ajustes conforme
                        revisão documental, particularidades técnicas do imóvel, exigências de campo,
                        cartório, certificações e demais condições específicas do processo.
                    </p>
                </div>

                <div class="footer">
                    <strong>GeoINCRA</strong><br/>
                    Documento gerado automaticamente pelo sistema<br/>
                    Pipeline de cálculo, automação e engenharia documental
                </div>
            </div>

        </div>
    </body>
    </html>
    """

    HTML(string=html).write_pdf(str(file_path))

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

    HTML(string=html).write_pdf(str(file_path))

    return str(file_path.relative_to(base_root))