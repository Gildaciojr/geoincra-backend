from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
from datetime import datetime


class MatriculaPdfService:

    BASE_UPLOAD_DIR = "app/uploads/imoveis"

    @staticmethod
    def gerar_pdf(imovel_id: int, dados: dict) -> dict:

        if not isinstance(dados, dict):
            raise Exception("Dados inválidos para geração do PDF da matrícula.")

        pasta = f"{MatriculaPdfService.BASE_UPLOAD_DIR}/{imovel_id}/matricula"
        os.makedirs(pasta, exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        nome = f"matricula_{timestamp}.pdf"

        caminho = f"{pasta}/{nome}"

        c = canvas.Canvas(caminho, pagesize=A4)

        y = 800

        def linha(txt):
            nonlocal y
            c.drawString(50, y, str(txt or ""))
            y -= 20

        numero_matricula = (
            dados.get("numero_matricula")
            or dados.get("matricula")
            or ""
        )

        comarca = dados.get("comarca") or ""
        livro = dados.get("livro") or ""
        folha = dados.get("folha") or ""

        confrontantes = dados.get("confrontantes") or []

        linha("MATRÍCULA DO IMÓVEL")
        linha("")

        linha(f"Número: {numero_matricula}")
        linha(f"Comarca: {comarca}")
        linha(f"Livro: {livro}")
        linha(f"Folha: {folha}")

        linha("")
        linha("CONFRONTANTES:")

        if isinstance(confrontantes, list):
            for cft in confrontantes:
                if not isinstance(cft, dict):
                    continue

                direcao = cft.get("direcao") or cft.get("lado") or ""
                nome = cft.get("nome") or ""

                if direcao or nome:
                    linha(f"{direcao} - {nome}")

        c.save()

        base_url = "https://geoincra.escriturafacil.com"
        url = f"{base_url}/{caminho.replace('app/', '')}"

        return {
            "arquivo_path": caminho,
            "arquivo_url": url,
        }