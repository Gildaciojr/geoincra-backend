from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
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

        largura, altura = A4

        # =========================================================
        # CONTROLE DE POSIÇÃO
        # =========================================================
        y = altura - 30 * mm

        def nova_linha(espaco=6):
            nonlocal y
            y -= espaco * mm

            if y < 30 * mm:
                c.showPage()
                y = altura - 30 * mm

        def escrever(texto, x=20, tamanho=10, bold=False):
            nonlocal y

            fonte = "Helvetica-Bold" if bold else "Helvetica"
            c.setFont(fonte, tamanho)
            c.drawString(x * mm, y, str(texto or ""))

        def titulo(texto):
            escrever(texto, tamanho=14, bold=True)
            nova_linha(10)

        def subtitulo(texto):
            escrever(texto, tamanho=11, bold=True)
            nova_linha(8)

        def linha_texto(texto):
            escrever(texto, tamanho=10)
            nova_linha(6)

        # =========================================================
        # DADOS
        # =========================================================

        numero_matricula = (
            dados.get("numero_matricula")
            or dados.get("matricula")
            or ""
        )

        comarca = dados.get("comarca") or ""
        livro = dados.get("livro") or ""
        folha = dados.get("folha") or ""
        codigo_cartorio = dados.get("codigo_cartorio") or ""

        confrontantes = dados.get("confrontantes") or []
        proprietarios = dados.get("proprietarios") or []

        # =========================================================
        # HEADER
        # =========================================================

        titulo("MATRÍCULA DO IMÓVEL")

        linha_texto(f"Número da Matrícula: {numero_matricula}")
        linha_texto(f"Comarca: {comarca}")
        linha_texto(f"Cartório: {codigo_cartorio}")
        linha_texto(f"Livro: {livro}")
        linha_texto(f"Folha: {folha}")

        nova_linha(10)

        # =========================================================
        # PROPRIETÁRIOS
        # =========================================================

        if isinstance(proprietarios, list) and proprietarios:
            subtitulo("PROPRIETÁRIOS")

            for p in proprietarios:

                if not isinstance(p, dict):
                    continue

                nome = p.get("nome") or ""
                cpf = p.get("cpf_cnpj") or ""
                tipo = p.get("tipo") or ""

                linha = f"{nome}"

                if cpf:
                    linha += f" | CPF/CNPJ: {cpf}"

                if tipo:
                    linha += f" | Tipo: {tipo}"

                linha_texto(f"- {linha}")

            nova_linha(6)

        # =========================================================
        # CONFRONTANTES
        # =========================================================

        if isinstance(confrontantes, list) and confrontantes:
            subtitulo("CONFRONTANTES")

            for cft in confrontantes:

                if not isinstance(cft, dict):
                    continue

                direcao = (
                    cft.get("direcao")
                    or cft.get("lado")
                    or ""
                )

                nome = cft.get("nome") or ""
                matricula_cft = cft.get("matricula") or ""
                descricao = cft.get("descricao") or ""
                identificacao = cft.get("identificacao") or ""

                partes = []

                if direcao:
                    partes.append(f"{direcao}")

                if nome:
                    partes.append(nome)

                if matricula_cft:
                    partes.append(f"Matrícula: {matricula_cft}")

                if identificacao:
                    partes.append(f"ID: {identificacao}")

                if descricao:
                    partes.append(descricao)

                if partes:
                    linha_texto(f"- {' | '.join(partes)}")

            nova_linha(6)

        # =========================================================
        # RODAPÉ
        # =========================================================

        c.setFont("Helvetica", 8)
        c.drawString(
            20 * mm,
            15 * mm,
            f"Documento gerado automaticamente em {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC"
        )

        c.save()

        base_url = "https://geoincra.escriturafacil.com"
        url = f"{base_url}/{caminho.replace('app/', '')}"

        return {
            "arquivo_path": caminho,
            "arquivo_url": url,
        }