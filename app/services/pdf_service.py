# geoincra_backend/app/services/pdf_service.py
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE_UPLOAD_PATH = "/app/app/uploads/propostas"  # ✅ caminho absoluto correto


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


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


def gerar_pdf_proposta(project_id: int, html_simples: str) -> str:
    _ensure_dir(BASE_UPLOAD_PATH)

    filename = f"proposta_project_{project_id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = os.path.join(BASE_UPLOAD_PATH, filename)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 40

    for linha in _limpar_html_simples(html_simples):
        if not linha.strip():
            y -= 10
            continue

        c.drawString(40, y, linha.strip())
        y -= 14

        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    return file_path


def gerar_pdf_contrato(project_id: int, html_simples: str) -> str:
    _ensure_dir(BASE_UPLOAD_PATH)

    filename = f"contrato_project_{project_id}_{int(datetime.utcnow().timestamp())}.pdf"
    file_path = os.path.join(BASE_UPLOAD_PATH, filename)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 40

    for linha in _limpar_html_simples(html_simples):
        if not linha.strip():
            y -= 10
            continue

        c.drawString(40, y, linha.strip())
        y -= 14

        if y < 40:
            c.showPage()
            y = height - 40

    c.save()
    return file_path
