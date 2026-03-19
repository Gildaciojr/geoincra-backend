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
# 📄 ORÇAMENTO (mantido em reportlab)
# =========================================================
def gerar_pdf_orcamento(calculation) -> str:
    base = _resolve_base() / "orcamentos" / "preview"
    _ensure_dir(base)

    filename = f"orcamento_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = base / filename

    c = canvas.Canvas(str(file_path), pagesize=A4)
    width, height = A4
    y = height - 40

    linhas = [
        "ORÇAMENTO – GEOINCRA",
        "",
        f"Valor base: R$ {calculation.valor_base:.2f}",
        f"ART: R$ {calculation.valor_art:.2f}",
        f"Custos adicionais: R$ {(calculation.valor_variaveis_fixas + calculation.valor_variaveis_percentuais):.2f}",
        f"Cartório: R$ {calculation.valor_cartorio:.2f}",
        "",
        f"TOTAL: R$ {calculation.total_final:.2f}",
        "",
        "Este orçamento não constitui contrato.",
        "Validade: 60 dias.",
    ]

    for linha in linhas:
        c.drawString(40, y, linha)
        y -= 16
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    return str(file_path)


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