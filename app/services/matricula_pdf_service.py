from __future__ import annotations

import os
from datetime import datetime
from typing import Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas


class MatriculaPdfService:
    BASE_UPLOAD_DIR = "app/uploads/imoveis"
    BASE_URL = "https://geoincra.escriturafacil.com"

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

        margem_esquerda = 18 * mm
        margem_direita = 18 * mm
        margem_superior = 18 * mm
        margem_inferior = 16 * mm
        largura_util = largura - margem_esquerda - margem_direita

        y = altura - margem_superior

        styles = getSampleStyleSheet()

        style_bloco = ParagraphStyle(
            name="BlocoTexto",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=0,
            spaceBefore=0,
        )

        style_bloco_bold = ParagraphStyle(
            name="BlocoTextoBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
            spaceAfter=0,
            spaceBefore=0,
        )

        style_titulo_secao = ParagraphStyle(
            name="TituloSecao",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.white,
            alignment=0,
        )

        style_texto_livre = ParagraphStyle(
            name="TextoLivre",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1F2937"),
            alignment=4,
        )

        def _safe_text(valor: Any) -> str:
            if valor is None:
                return ""
            return " ".join(str(valor).strip().split())

        def _safe_upper(valor: Any) -> str:
            return _safe_text(valor).upper()

        def _paragraph_height(texto: str, style: ParagraphStyle, width: float) -> float:
            p = Paragraph(texto, style)
            _, h = p.wrap(width, 10000)
            return h

        def _draw_paragraph(
            texto: str,
            x: float,
            y_top: float,
            width: float,
            style: ParagraphStyle,
        ) -> float:
            p = Paragraph(texto, style)
            _, h = p.wrap(width, 10000)
            p.drawOn(c, x, y_top - h)
            return h

        def _nova_pagina():
            nonlocal y
            c.showPage()
            y = altura - margem_superior
            _draw_page_frame()

        def _garantir_espaco(altura_necessaria: float):
            nonlocal y
            if y - altura_necessaria < margem_inferior:
                _nova_pagina()

        def _draw_page_frame():
            c.setStrokeColor(colors.HexColor("#D1D5DB"))
            c.setLineWidth(0.6)
            c.rect(
                12 * mm,
                12 * mm,
                largura - 24 * mm,
                altura - 24 * mm,
                stroke=1,
                fill=0,
            )

        def _draw_header_principal():
            nonlocal y

            altura_header = 24 * mm
            _garantir_espaco(altura_header + 8 * mm)

            c.setFillColor(colors.HexColor("#0F172A"))
            c.roundRect(
                margem_esquerda,
                y - altura_header,
                largura_util,
                altura_header,
                3 * mm,
                stroke=0,
                fill=1,
            )

            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 15)
            c.drawString(
                margem_esquerda + 6 * mm,
                y - 8.5 * mm,
                "MATRÍCULA DO IMÓVEL",
            )

            c.setFont("Helvetica", 8.5)
            c.drawRightString(
                margem_esquerda + largura_util - 6 * mm,
                y - 8.5 * mm,
                "GeoINCRA • Documento Técnico Gerado Automaticamente",
            )

            c.setStrokeColor(colors.HexColor("#334155"))
            c.setLineWidth(0.5)
            c.line(
                margem_esquerda + 6 * mm,
                y - 12.5 * mm,
                margem_esquerda + largura_util - 6 * mm,
                y - 12.5 * mm,
            )

            c.setFont("Helvetica", 8.5)
            c.drawString(
                margem_esquerda + 6 * mm,
                y - 18.2 * mm,
                f"Imóvel ID: {imovel_id}",
            )

            c.drawRightString(
                margem_esquerda + largura_util - 6 * mm,
                y - 18.2 * mm,
                datetime.utcnow().strftime("Gerado em %d/%m/%Y às %H:%M:%S UTC"),
            )

            y -= altura_header + 6 * mm

        def _draw_section_title(titulo: str):
            nonlocal y

            altura_bloco = 8.5 * mm
            _garantir_espaco(altura_bloco + 3 * mm)

            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.roundRect(
                margem_esquerda,
                y - altura_bloco,
                largura_util,
                altura_bloco,
                2 * mm,
                stroke=0,
                fill=1,
            )

            _draw_paragraph(
                titulo,
                margem_esquerda + 4 * mm,
                y - 1.4 * mm,
                largura_util - 8 * mm,
                style_titulo_secao,
            )

            y -= altura_bloco + 3 * mm

        def _draw_info_table(linhas: List[List[str]], col_widths: List[float]):
            nonlocal y

            tabela = Table(linhas, colWidths=col_widths, repeatRows=0)
            tabela.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )

            largura_tabela, altura_tabela = tabela.wrap(largura_util, 10000)
            _garantir_espaco(altura_tabela + 2 * mm)
            tabela.drawOn(c, margem_esquerda, y - altura_tabela)
            y -= altura_tabela + 3 * mm

        def _draw_text_box(textos: List[str]):
            nonlocal y

            textos_validos = [t for t in textos if _safe_text(t)]
            if not textos_validos:
                return

            largura_interna = largura_util - 8 * mm
            alturas = [
                _paragraph_height(t, style_texto_livre, largura_interna)
                for t in textos_validos
            ]
            altura_total = sum(alturas) + (len(alturas) - 1) * 2 + 8 * mm

            _garantir_espaco(altura_total)

            c.setFillColor(colors.HexColor("#FFFFFF"))
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(0.6)
            c.roundRect(
                margem_esquerda,
                y - altura_total,
                largura_util,
                altura_total,
                2 * mm,
                stroke=1,
                fill=1,
            )

            y_cursor = y - 4 * mm

            for texto in textos_validos:
                h = _draw_paragraph(
                    texto,
                    margem_esquerda + 4 * mm,
                    y_cursor,
                    largura_interna,
                    style_texto_livre,
                )
                y_cursor -= h + 2

            y -= altura_total + 3 * mm

        def _draw_table_with_header(
            headers: List[str],
            rows: List[List[str]],
            col_widths: List[float],
        ):
            nonlocal y

            data = [headers] + rows

            tabela = Table(data, colWidths=col_widths, repeatRows=1)
            tabela.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ]
                )
            )

            largura_tabela, altura_tabela = tabela.wrap(largura_util, 10000)
            _garantir_espaco(altura_tabela + 2 * mm)
            tabela.drawOn(c, margem_esquerda, y - altura_tabela)
            y -= altura_tabela + 3 * mm

        def _draw_footer():
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(0.5)
            c.line(
                margem_esquerda,
                18 * mm,
                margem_esquerda + largura_util,
                18 * mm,
            )

            c.setFont("Helvetica", 7.5)
            c.setFillColor(colors.HexColor("#475569"))
            c.drawString(
                margem_esquerda,
                14.5 * mm,
                "GeoINCRA • Matrícula técnica gerada automaticamente pelo pipeline OCR + IA.",
            )

            c.drawRightString(
                margem_esquerda + largura_util,
                14.5 * mm,
                datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S UTC"),
            )

        # =========================================================
        # NORMALIZAÇÃO DOS DADOS DE ENTRADA
        # =========================================================
        numero_matricula = _safe_text(
            dados.get("numero_matricula") or dados.get("matricula")
        )
        comarca = _safe_text(dados.get("comarca"))
        livro = _safe_text(dados.get("livro"))
        folha = _safe_text(dados.get("folha"))
        codigo_cartorio = _safe_text(dados.get("codigo_cartorio"))
        status = _safe_text(dados.get("status"))

        confrontantes = dados.get("confrontantes") or []
        proprietarios = dados.get("proprietarios") or []

        if not isinstance(confrontantes, list):
            confrontantes = []

        if not isinstance(proprietarios, list):
            proprietarios = []

        # =========================================================
        # PÁGINA
        # =========================================================
        _draw_page_frame()
        _draw_header_principal()

        # =========================================================
        # SEÇÃO — IDENTIFICAÇÃO DA MATRÍCULA
        # =========================================================
        _draw_section_title("1. IDENTIFICAÇÃO DA MATRÍCULA")

        info_linhas = [
            [
                Paragraph("<b>Número da Matrícula</b>", style_bloco_bold),
                Paragraph(numero_matricula or "NÃO INFORMADO", style_bloco),
                Paragraph("<b>Comarca</b>", style_bloco_bold),
                Paragraph(comarca or "NÃO INFORMADO", style_bloco),
            ],
            [
                Paragraph("<b>Livro</b>", style_bloco_bold),
                Paragraph(livro or "NÃO INFORMADO", style_bloco),
                Paragraph("<b>Folha</b>", style_bloco_bold),
                Paragraph(folha or "NÃO INFORMADO", style_bloco),
            ],
            [
                Paragraph("<b>Código do Cartório</b>", style_bloco_bold),
                Paragraph(codigo_cartorio or "NÃO INFORMADO", style_bloco),
                Paragraph("<b>Status</b>", style_bloco_bold),
                Paragraph(status or "NÃO INFORMADO", style_bloco),
            ],
        ]

        _draw_info_table(
            linhas=info_linhas,
            col_widths=[
                36 * mm,
                54 * mm,
                32 * mm,
                largura_util - (36 * mm + 54 * mm + 32 * mm),
            ],
        )

        # =========================================================
        # SEÇÃO — PROPRIETÁRIOS
        # =========================================================
        _draw_section_title("2. PROPRIETÁRIOS")

        proprietarios_rows: List[List[str]] = []

        if proprietarios:
            for idx, p in enumerate(proprietarios, start=1):
                if not isinstance(p, dict):
                    continue

                nome = _safe_text(p.get("nome"))
                cpf_cnpj = _safe_text(p.get("cpf_cnpj"))
                tipo = _safe_text(p.get("tipo"))

                proprietarios_rows.append(
                    [
                        str(idx),
                        nome or "NÃO INFORMADO",
                        cpf_cnpj or "NÃO INFORMADO",
                        tipo or "NÃO INFORMADO",
                    ]
                )

        if proprietarios_rows:
            _draw_table_with_header(
                headers=["#", "Nome", "CPF/CNPJ", "Tipo"],
                rows=proprietarios_rows,
                col_widths=[10 * mm, 82 * mm, 42 * mm, largura_util - (10 * mm + 82 * mm + 42 * mm)],
            )
        else:
            _draw_text_box(
                [
                    "Não foram identificados proprietários válidos para compor esta matrícula técnica."
                ]
            )

        # =========================================================
        # SEÇÃO — CONFRONTANTES
        # =========================================================
        _draw_section_title("3. CONFRONTANTES")

        confrontantes_rows: List[List[str]] = []

        if confrontantes:
            for idx, cft in enumerate(confrontantes, start=1):
                if not isinstance(cft, dict):
                    continue

                direcao = _safe_text(cft.get("direcao") or cft.get("lado"))
                nome = _safe_text(cft.get("nome"))
                matricula_cft = _safe_text(cft.get("matricula"))
                identificacao = _safe_text(cft.get("identificacao"))
                descricao = _safe_text(cft.get("descricao"))

                descricao_composta_partes: List[str] = []

                if identificacao:
                    descricao_composta_partes.append(f"ID/Imóvel: {identificacao}")

                if matricula_cft:
                    descricao_composta_partes.append(f"Matrícula: {matricula_cft}")

                if descricao:
                    descricao_composta_partes.append(descricao)

                descricao_composta = " | ".join(descricao_composta_partes)

                confrontantes_rows.append(
                    [
                        str(idx),
                        direcao or "NÃO INFORMADO",
                        nome or "NÃO INFORMADO",
                        descricao_composta or "NÃO INFORMADO",
                    ]
                )

        if confrontantes_rows:
            _draw_table_with_header(
                headers=["#", "Direção", "Confrontante", "Detalhamento Técnico"],
                rows=confrontantes_rows,
                col_widths=[10 * mm, 24 * mm, 46 * mm, largura_util - (10 * mm + 24 * mm + 46 * mm)],
            )
        else:
            _draw_text_box(
                [
                    "Não foram identificados confrontantes válidos para compor esta matrícula técnica."
                ]
            )

        # =========================================================
        # SEÇÃO — OBSERVAÇÃO TÉCNICA
        # =========================================================
        _draw_section_title("4. OBSERVAÇÃO TÉCNICA")

        observacoes_bloco: List[str] = [
            (
                "Este documento foi gerado automaticamente pelo módulo técnico do GeoINCRA, "
                "a partir do processamento do OCR estruturado e da consolidação dos dados "
                "registrados para a matrícula do imóvel."
            ),
            (
                "Recomenda-se conferência jurídica e técnica do conteúdo antes de utilização "
                "como peça final de instrução, protocolo, validação cartorial ou conferência "
                "de campo."
            ),
        ]

        if numero_matricula:
            observacoes_bloco.insert(
                0,
                f"Matrícula de referência: {numero_matricula}.",
            )

        _draw_text_box(observacoes_bloco)

        # =========================================================
        # RODAPÉ
        # =========================================================
        _draw_footer()

        c.save()

        url = f"{MatriculaPdfService.BASE_URL}/{caminho.replace('app/', '')}"

        return {
            "arquivo_path": caminho,
            "arquivo_url": url,
        }