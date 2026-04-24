from __future__ import annotations

import os
from datetime import datetime
from typing import Any, List, Optional
import cairosvg

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth


class MatriculaPdfService:
    BASE_UPLOAD_DIR = "app/uploads/imoveis"
    BASE_URL = "https://geoincra.escriturafacil.com"

    # =========================================================
    # 🔥 HELPER — CROQUI SVG → PNG (INTEGRAÇÃO)
    # =========================================================
    @staticmethod
    def _gerar_croqui_png(imovel_id: int, dados: dict) -> Optional[str]:
        try:
            geojson = dados.get("geojson")
            if not geojson:
                return None

            from app.services.croqui_service import CroquiService

            svg = CroquiService.gerar_svg(
                geojson=geojson,
                confrontantes=dados.get("confrontantes") or [],
            )

            pasta = f"{MatriculaPdfService.BASE_UPLOAD_DIR}/{imovel_id}/croqui"
            os.makedirs(pasta, exist_ok=True)

            caminho_png = f"{pasta}/croqui.png"

            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                write_to=caminho_png,
            )

            return caminho_png

        except Exception as e:
            return None

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

        # =========================================================
        # 🔥 NORMALIZAÇÃO SEGURA (CRÍTICO PARA REPORTLAB)
        # =========================================================
        def _safe_text(valor: Any) -> str:
            if valor is None:
                return ""

            texto = " ".join(str(valor).strip().split())

            return (
                texto.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        def _safe_upper(valor: Any) -> str:
            return _safe_text(valor).upper()

        def _paragraph_height(texto: str, style: ParagraphStyle, width: float) -> float:
            p = Paragraph(texto or "", style)
            _, h = p.wrap(width, 10000)
            return h

        def _draw_paragraph(
            texto: str,
            x: float,
            y_top: float,
            width: float,
            style: ParagraphStyle,
        ) -> float:
            p = Paragraph(texto or "", style)
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

            titulo = _safe_text(titulo)
            if not titulo:
                return

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

            if not linhas:
                return

            linhas_seguras = []
            for linha in linhas:
                if not isinstance(linha, list):
                    continue

                linhas_seguras.append(
                    [
                        cell if isinstance(cell, Paragraph) else _safe_text(cell)
                        for cell in linha
                    ]
                )

            if not linhas_seguras:
                return

            tabela = Table(linhas_seguras, colWidths=col_widths, repeatRows=0)
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

            if not textos or not isinstance(textos, list):
                return

            textos_validos: List[str] = []

            for t in textos:
                try:
                    t_safe = _safe_text(t)
                    if t_safe:
                        textos_validos.append(t_safe)
                except Exception:
                    continue

            if not textos_validos:
                return

            largura_interna = largura_util - 8 * mm

            alturas: List[float] = []

            for t in textos_validos:
                try:
                    h = _paragraph_height(t, style_texto_livre, largura_interna)
                    if h <= 0:
                        h = 12
                    alturas.append(h)
                except Exception:
                    alturas.append(12)

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
                try:
                    h = _draw_paragraph(
                        texto,
                        margem_esquerda + 4 * mm,
                        y_cursor,
                        largura_interna,
                        style_texto_livre,
                    )
                except Exception:
                    h = 12

                y_cursor -= h + 2

            y -= altura_total + 3 * mm

        def _draw_table_with_header(
            headers: List[str],
            rows: List[List[str]],
            col_widths: List[float],
        ):
            nonlocal y

            if not headers or not isinstance(headers, list):
                return

            # 🔥 normalização defensiva dos headers
            headers_seguro: List[str] = []
            for h in headers:
                try:
                    headers_seguro.append(_safe_text(h))
                except Exception:
                    headers_seguro.append("")

            rows_seguras: List[List[str]] = []

            if rows and isinstance(rows, list):
                for r in rows:
                    if not isinstance(r, list):
                        continue

                    linha: List[str] = []

                    for i in range(len(headers_seguro)):
                        try:
                            valor = r[i] if i < len(r) else ""
                        except Exception:
                            valor = ""

                        try:
                            linha.append(_safe_text(valor))
                        except Exception:
                            linha.append("")

                    rows_seguras.append(linha)

            # evita tabela vazia (quebra visual)
            data = [headers_seguro] + (rows_seguras or [["" for _ in headers_seguro]])

            tabela = Table(data, colWidths=col_widths, repeatRows=1)

            tabela.setStyle(
                TableStyle(
                    [
                        # HEADER
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8.5),

                        # BODY
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8.5),

                        # GRID
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),

                        # PADDING
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),

                        # LINHAS ALTERNADAS
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                            colors.white,
                            colors.HexColor("#F8FAFC")
                        ]),
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

            texto_esquerda = "GeoINCRA • Matrícula técnica gerada automaticamente pelo pipeline OCR + IA."
            texto_direita = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S UTC")

            c.setFont("Helvetica", 7.5)
            c.setFillColor(colors.HexColor("#475569"))

            max_width = largura_util - 60 * mm

            texto_final = texto_esquerda
            while stringWidth(texto_final, "Helvetica", 7.5) > max_width and len(texto_final) > 10:
                texto_final = texto_final[:-1]

            if texto_final != texto_esquerda:
                texto_final = texto_final.rstrip() + "..."

            c.drawString(
                margem_esquerda,
                14.5 * mm,
                texto_final,
            )

            c.drawRightString(
                margem_esquerda + largura_util,
                14.5 * mm,
                texto_direita,
            )

        # =========================================================
        # NORMALIZAÇÃO DOS DADOS DE ENTRADA (UPGRADE COMPLETO)
        # =========================================================

        matricula_obj = dados.get("matricula") if isinstance(dados.get("matricula"), dict) else {}

        numero_matricula = _safe_text(
            dados.get("numero_matricula")
            or matricula_obj.get("numero")
            or dados.get("matricula")
            or dados.get("numero")
        )

        comarca = _safe_text(
            dados.get("comarca")
            or matricula_obj.get("comarca")
        )

        livro = _safe_text(dados.get("livro") or matricula_obj.get("livro"))
        folha = _safe_text(dados.get("folha") or matricula_obj.get("folha"))

        codigo_cartorio = _safe_text(dados.get("codigo_cartorio"))

        status = _safe_text(dados.get("status") or "ATIVA")

        # =========================================================
        # 🔥 IMÓVEL (UPGRADE)
        # =========================================================

        descricao_imovel = _safe_text(
            dados.get("descricao_imovel")
            or (dados.get("imovel") or {}).get("descricao")
        )

        area_total = dados.get("area_total")
        unidade_area = _safe_text(dados.get("unidade_area"))
        area_hectares = dados.get("area_hectares")

        # 🔥 montagem profissional da área
        area_formatada = None

        if area_hectares:
            try:
                area_formatada = f"{float(area_hectares):,.4f} ha".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                area_formatada = f"{area_hectares} ha"

        elif area_total and unidade_area:
            area_formatada = f"{area_total} {unidade_area}"

        # =========================================================
        # 🔥 MEMORIAL / GEOMETRIA
        # =========================================================

        memorial_texto = _safe_text(dados.get("memorial_texto"))
        possui_memorial = bool(memorial_texto)

        possui_geo = bool(dados.get("geojson"))

        # =========================================================
        # 🔥 LISTAS NORMALIZADAS
        # =========================================================

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
                Paragraph(status, style_bloco),
            ],
            [
                Paragraph("<b>Área do Imóvel</b>", style_bloco_bold),
                Paragraph(area_formatada or "NÃO INFORMADO", style_bloco),
                Paragraph("", style_bloco_bold),
                Paragraph("", style_bloco),
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
        # 🔥 NOVO — SEÇÃO IMÓVEL (CRÍTICO)
        # =========================================================
        _draw_section_title("2. IDENTIFICAÇÃO DO IMÓVEL")

        textos_imovel: List[str] = []

        if descricao_imovel:
            textos_imovel.append(f"<b>Descrição:</b> {descricao_imovel}")

        # 🔥 ÁREA PADRONIZADA
        if area_total:
            try:
                textos_imovel.append(
                    f"<b>Área original:</b> {area_total} {unidade_area or ''}".strip()
                )
            except Exception:
                textos_imovel.append("<b>Área original:</b> NÃO INFORMADO")

        if area_hectares:
            try:
                area_hectares_float = float(area_hectares)
                area_formatada = f"{area_hectares_float:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
                textos_imovel.append(
                    f"<b>Área oficial:</b> {area_formatada} hectares"
                )
            except Exception:
                textos_imovel.append("<b>Área oficial:</b> NÃO INFORMADO")

        if textos_imovel:
            _draw_text_box(textos_imovel)
        else:
            _draw_text_box(
                ["Não foi possível identificar dados completos do imóvel."]
            )

        # =========================================================
        # SEÇÃO — PROPRIETÁRIOS
        # =========================================================
        _draw_section_title("3. PROPRIETÁRIOS")

        proprietarios_rows: List[List[str]] = []

        if proprietarios:
            for idx, p in enumerate(proprietarios, start=1):

                if not isinstance(p, dict):
                    continue

                nome = _safe_text(p.get("nome"))
                cpf_cnpj = _safe_text(p.get("cpf_cnpj"))

                tipo_raw = str(p.get("tipo") or "").upper().strip()

                # 🔥 NORMALIZAÇÃO PROFISSIONAL DO TIPO
                if tipo_raw in ["PF", "FISICA"]:
                    tipo = "Pessoa Física"
                elif tipo_raw in ["PJ", "JURIDICA"]:
                    tipo = "Pessoa Jurídica"
                else:
                    tipo = "NÃO INFORMADO"

                if not nome and not cpf_cnpj:
                    continue

                proprietarios_rows.append(
                    [
                        str(idx),
                        nome or "NÃO INFORMADO",
                        cpf_cnpj or "NÃO INFORMADO",
                        tipo,
                    ]
                )

        if proprietarios_rows:
            _draw_table_with_header(
                headers=["#", "Nome", "CPF/CNPJ", "Tipo"],
                rows=proprietarios_rows,
                col_widths=[
                    10 * mm,
                    82 * mm,
                    42 * mm,
                    largura_util - (10 * mm + 82 * mm + 42 * mm),
                ],
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
        _draw_section_title("4. CONFRONTANTES")

        confrontantes_rows: List[List[str]] = []

        if confrontantes:
            for idx, cft in enumerate(confrontantes, start=1):

                if not isinstance(cft, dict):
                    continue

                try:
                    direcao_raw = (
                        cft.get("lado_normalizado")
                        or cft.get("direcao")
                        or cft.get("lado")
                    )

                    direcao = _safe_upper(direcao_raw)

                except Exception:
                    direcao = ""

                try:
                    nome = _safe_text(cft.get("nome"))
                except Exception:
                    nome = ""

                try:
                    matricula_cft = _safe_text(cft.get("matricula"))
                except Exception:
                    matricula_cft = ""

                try:
                    identificacao = _safe_text(cft.get("identificacao"))
                except Exception:
                    identificacao = ""

                try:
                    descricao = _safe_text(cft.get("descricao"))
                except Exception:
                    descricao = ""

                # 🔥 NOVOS CAMPOS (OCR V2)
                try:
                    tipo = _safe_text(cft.get("tipo"))
                except Exception:
                    tipo = ""

                try:
                    lote = _safe_text(cft.get("lote"))
                except Exception:
                    lote = ""

                try:
                    gleba = _safe_text(cft.get("gleba"))
                except Exception:
                    gleba = ""

                if not any([nome, matricula_cft, identificacao, descricao]):
                    continue

                descricao_composta_partes: List[str] = []

                if identificacao:
                    descricao_composta_partes.append(f"Imóvel: {identificacao}")

                if matricula_cft:
                    descricao_composta_partes.append(f"Matrícula: {matricula_cft}")

                if lote:
                    descricao_composta_partes.append(f"Lote: {lote}")

                if gleba:
                    descricao_composta_partes.append(f"Gleba: {gleba}")

                if tipo:
                    descricao_composta_partes.append(f"Tipo: {tipo}")

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
                col_widths=[
                    10 * mm,
                    24 * mm,
                    46 * mm,
                    largura_util - (10 * mm + 24 * mm + 46 * mm),
                ],
            )
        else:
            _draw_text_box(
                [
                    "Não foram identificados confrontantes válidos para compor esta matrícula técnica."
                ]
            )

        # =========================================================
        # 🔥 NOVO — ANÁLISE JURÍDICA (PRIORIDADE 02)
        # =========================================================
        try:
            from app.services.matricula_analysis_service import MatriculaAnalysisService

            # 🔥 TEXTO BASE ROBUSTO (ORDEM INTELIGENTE)
            texto_base = (
                dados.get("inteiro_teor")
                or dados.get("memorial_texto")
                or dados.get("descricao_imovel")
                or ""
            )

            analise = MatriculaAnalysisService.analisar(
                texto=texto_base,
            )

            _draw_section_title("5. ANÁLISE JURÍDICA E HISTÓRICO REGISTRAL")

            blocos_analise: List[str] = []

            classificacao = analise.get("classificacao") or {}

            status = str(classificacao.get("status") or "NÃO DEFINIDO").upper()
            score = int(analise.get("score_juridico") or 0)

            blocos_analise.append(
                f"<b>Status jurídico:</b> {status}"
            )

            blocos_analise.append(
                f"<b>Score jurídico:</b> {score} / 100"
            )

            # =========================================================
            # 🔥 REGISTROS E AVERBAÇÕES (SUBSTITUI HISTÓRICO)
            # =========================================================
            registros = analise.get("registros") or []
            averbacoes = analise.get("averbacoes") or []

            if registros or averbacoes:
                blocos_analise.append("<b>Atos registrais identificados:</b>")

                for r in registros[:10]:
                    blocos_analise.append(f"- Registro: {r}")

                for a in averbacoes[:10]:
                    blocos_analise.append(f"- Averbação: {a}")

            # =========================================================
            # ÔNUS
            # =========================================================
            onus = analise.get("onus") or []

            if onus:
                blocos_analise.append("<b>Ônus identificados:</b>")
                for o in onus:
                    blocos_analise.append(f"- {o}")

            # =========================================================
            # RISCOS
            # =========================================================
            riscos = analise.get("riscos") or []

            if riscos:
                blocos_analise.append("<b>Riscos jurídicos:</b>")
                for r in riscos:
                    blocos_analise.append(f"- {r}")

            # =========================================================
            # 🔥 ENRIQUECIMENTO VIA OCR (INTEGRAÇÃO REAL)
            # =========================================================
            proprietarios_ocr = dados.get("proprietarios") or []
            confrontantes_ocr = dados.get("confrontantes") or []

            if proprietarios_ocr:
                blocos_analise.append("<b>Proprietários identificados via OCR:</b>")
                blocos_analise.append(f"- Total: {len(proprietarios_ocr)}")

            if confrontantes_ocr:
                blocos_analise.append("<b>Confrontantes identificados:</b>")
                blocos_analise.append(f"- Total: {len(confrontantes_ocr)}")

            # =========================================================
            # FALLBACK
            # =========================================================
            if not blocos_analise:
                blocos_analise.append("Nenhuma informação jurídica relevante identificada.")

            _draw_text_box(blocos_analise)

        except Exception as exc:
            _draw_text_box(
                [f"Erro ao gerar análise jurídica: {str(exc)}"]
            )

        # =========================================================
        # 🔥 MEMORIAL DESCRITIVO (AJUSTADO PARA SEÇÃO 6)
        # =========================================================
        if possui_memorial:
            _draw_section_title("6. MEMORIAL DESCRITIVO")

            memorial_final = memorial_texto or ""

            # =========================================================
            # 🔥 INTEGRAÇÃO COM COORDENADAS TÉCNICAS (TXT/LISP)
            # =========================================================
            try:
                from app.services.txt_lisp_service import TxtLispService

                geojson = (
                    dados.get("geojson")
                    or (dados.get("geometria") or {}).get("geojson")
                    if isinstance(dados, dict)
                    else None
                )

                if geojson:
                    txt_vertices = TxtLispService.gerar_txt(geojson)

                    linhas = txt_vertices.split("\n")

                    linhas_vertices = [
                        l.strip()
                        for l in linhas
                        if l.strip().startswith("V")
                    ]

                    if linhas_vertices:
                        bloco_vertices = "\n".join(linhas_vertices)

                        memorial_final += (
                            "\n\n"
                            "------------------------------------------------------------\n"
                            "COORDENADAS DOS VÉRTICES (FORMATO TÉCNICO):\n\n"
                            f"{bloco_vertices}\n"
                            "------------------------------------------------------------"
                        )

            except Exception:
                memorial_final += (
                    "\n\n[AVISO TÉCNICO] Não foi possível gerar o bloco de coordenadas."
                )

            # =========================================================
            # 🔥 CONTROLE DE TAMANHO (EVITA QUEBRAR PDF)
            # =========================================================
            try:
                if len(memorial_final) > 12000:
                    partes = [
                        memorial_final[i:i+4000]
                        for i in range(0, len(memorial_final), 4000)
                    ]

                    for parte in partes:
                        _draw_text_box([parte])
                else:
                    _draw_text_box([memorial_final])

            except Exception:
                _draw_text_box([
                    "Erro ao renderizar memorial descritivo.",
                    "Verifique a integridade dos dados processados."
                ])

        # =========================================================
        # SEÇÃO — OBSERVAÇÃO TÉCNICA
        # =========================================================
        _draw_section_title("7. OBSERVAÇÃO TÉCNICA")

        observacoes_bloco: List[str] = [
            (
                "Este documento foi gerado automaticamente pelo módulo técnico do GeoINCRA, "
                "a partir do processamento estruturado de OCR, análise dos dados e "
                "consolidação das informações vinculadas à matrícula do imóvel."
            ),
            (
                "As informações aqui apresentadas possuem caráter técnico informativo, "
                "devendo ser validadas por profissional habilitado antes de qualquer "
                "utilização para fins legais, cartoriais ou operacionais."
            ),
        ]

        # =========================================================
        # CONTEXTO DA MATRÍCULA
        # =========================================================
        if numero_matricula:
            observacoes_bloco.insert(
                0,
                f"Matrícula de referência: {numero_matricula}.",
            )

        _draw_text_box(observacoes_bloco)

        # =========================================================
        # 🔥 CROQUI DO IMÓVEL (INTEGRAÇÃO FINAL)
        # =========================================================
        if possui_geo:

            croqui_path = None

            try:
                croqui_path = MatriculaPdfService._gerar_croqui_png(imovel_id, dados)
            except Exception:
                croqui_path = None

            if croqui_path and os.path.exists(croqui_path):

                _draw_section_title("8. CROQUI DO IMÓVEL")

                largura_img = largura_util
                altura_img = largura_img * 0.75

                _garantir_espaco(altura_img + 10 * mm)

                try:
                    c.drawImage(
                        croqui_path,
                        margem_esquerda,
                        y - altura_img,
                        width=largura_img,
                        height=altura_img,
                        preserveAspectRatio=True,
                        mask='auto'
                    )

                    y -= altura_img + 6 * mm

                except Exception:
                    _draw_text_box(
                        ["Erro ao renderizar croqui do imóvel."]
                    )

            else:
                _draw_text_box(
                    [
                        "Croqui não disponível para este imóvel.",
                        "Verifique se a geometria foi corretamente gerada no pipeline."
                    ]
                )
                
        # =========================================================
        # RODAPÉ
        # =========================================================
        _draw_footer()

        # =========================================================
        # FINALIZAÇÃO SEGURA
        # =========================================================
        try:
            c.save()
        except Exception as e:
            raise Exception(f"Erro ao finalizar PDF: {str(e)}")

        # =========================================================
        # URL FINAL
        # =========================================================
        caminho_relativo = caminho.replace("app/", "") if "app/" in caminho else caminho
        url = f"{MatriculaPdfService.BASE_URL}/{caminho_relativo}"

        return {
            "arquivo_path": caminho,
            "arquivo_url": url,
        }