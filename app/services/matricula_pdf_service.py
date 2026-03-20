from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
from datetime import datetime


class MatriculaPdfService:

    BASE_UPLOAD_DIR = "app/uploads/imoveis"

    @staticmethod
    def gerar_pdf(imovel_id: int, dados: dict) -> dict:

        pasta = f"{MatriculaPdfService.BASE_UPLOAD_DIR}/{imovel_id}/matricula"
        os.makedirs(pasta, exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        nome = f"matricula_{timestamp}.pdf"

        caminho = f"{pasta}/{nome}"

        c = canvas.Canvas(caminho, pagesize=A4)

        y = 800

        def linha(txt):
            nonlocal y
            c.drawString(50, y, txt)
            y -= 20

        linha("MATRÍCULA DO IMÓVEL")
        linha("")

        linha(f"Número: {dados.get('matricula')}")
        linha(f"Comarca: {dados.get('comarca')}")
        linha(f"Livro: {dados.get('livro')}")
        linha(f"Folha: {dados.get('folha')}")

        linha("")
        linha("CONFRONTANTES:")

        for cft in dados.get("confrontantes", []):
            linha(f"{cft.get('direcao')} - {cft.get('nome')}")

        c.save()

        url = caminho.replace("app/", "/")

        return {
            "arquivo_path": caminho,
            "arquivo_url": url,
        }