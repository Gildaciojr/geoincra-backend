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

            altura_header = 28 * mm
            _garantir_espaco(altura_header + 10 * mm)

            # =========================================================
            # FUNDO PRINCIPAL
            # =========================================================
            c.setFillColor(colors.HexColor("#0B1F3A"))
            c.roundRect(
                margem_esquerda,
                y - altura_header,
                largura_util,
                altura_header,
                3 * mm,
                stroke=0,
                fill=1,
            )

            # =========================================================
            # FAIXA SUPERIOR (IDENTIDADE)
            # =========================================================
            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.rect(
                margem_esquerda,
                y - 6 * mm,
                largura_util,
                6 * mm,
                stroke=0,
                fill=1,
            )

            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(
                margem_esquerda + 5 * mm,
                y - 4.2 * mm,
                "SISTEMA GEOINCRA • ENGENHARIA DE DOCUMENTOS • GEORREFERENCIAMENTO"
            )

            # =========================================================
            # TÍTULO PRINCIPAL
            # =========================================================
            c.setFont("Helvetica-Bold", 16)
            c.drawString(
                margem_esquerda + 6 * mm,
                y - 12.5 * mm,
                "MATRÍCULA DO IMÓVEL RURAL",
            )

            # =========================================================
            # SUBTÍTULO TÉCNICO
            # =========================================================
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.HexColor("#E2E8F0"))
            c.drawString(
                margem_esquerda + 6 * mm,
                y - 17.5 * mm,
                "Documento técnico estruturado com base em OCR, análise jurídica e processamento geoespacial",
            )

            # =========================================================
            # LINHA DIVISÓRIA INTERNA
            # =========================================================
            c.setStrokeColor(colors.HexColor("#334155"))
            c.setLineWidth(0.6)
            c.line(
                margem_esquerda + 6 * mm,
                y - 20 * mm,
                margem_esquerda + largura_util - 6 * mm,
                y - 20 * mm,
            )

            # =========================================================
            # BLOCO INFERIOR ESQUERDO
            # =========================================================
            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.white)
            c.drawString(
                margem_esquerda + 6 * mm,
                y - 24 * mm,
                f"Identificação do imóvel: ID {imovel_id}",
            )

            # =========================================================
            # BLOCO INFERIOR DIREITO
            # =========================================================
            c.drawRightString(
                margem_esquerda + largura_util - 6 * mm,
                y - 24 * mm,
                datetime.utcnow().strftime("Emitido em %d/%m/%Y • %H:%M:%S UTC"),
            )

            # =========================================================
            # BORDA EXTERNA
            # =========================================================
            c.setStrokeColor(colors.HexColor("#1E293B"))
            c.setLineWidth(0.6)
            c.roundRect(
                margem_esquerda,
                y - altura_header,
                largura_util,
                altura_header,
                3 * mm,
                stroke=1,
                fill=0,
            )

            y -= altura_header + 6 * mm

        def _draw_section_title(titulo: str):
            nonlocal y

            titulo = _safe_text(titulo)
            if not titulo:
                return

            altura_bloco = 10 * mm
            _garantir_espaco(altura_bloco + 4 * mm)

            # =========================================================
            # FUNDO PRINCIPAL
            # =========================================================
            c.setFillColor(colors.HexColor("#0F172A"))
            c.roundRect(
                margem_esquerda,
                y - altura_bloco,
                largura_util,
                altura_bloco,
                2 * mm,
                stroke=0,
                fill=1,
            )

            # =========================================================
            # FAIXA LATERAL (IDENTIDADE VISUAL)
            # =========================================================
            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.rect(
                margem_esquerda,
                y - altura_bloco,
                4 * mm,
                altura_bloco,
                stroke=0,
                fill=1,
            )

            # =========================================================
            # TEXTO
            # =========================================================
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.white)
            c.drawString(
                margem_esquerda + 6 * mm,
                y - 6.5 * mm,
                titulo.upper(),
            )

            # =========================================================
            # LINHA INFERIOR SUAVE (REFINO)
            # =========================================================
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(0.6)
            c.line(
                margem_esquerda,
                y - altura_bloco - 1.2 * mm,
                margem_esquerda + largura_util,
                y - altura_bloco - 1.2 * mm,
            )

            y -= altura_bloco + 4 * mm

        def _draw_info_table(linhas: List[List[str]], col_widths: List[float]):
            nonlocal y

            if not linhas:
                return

            linhas_seguras = []

            for linha in linhas:
                if not isinstance(linha, list):
                    continue

                linha_segura = []
                for cell in linha:
                    if isinstance(cell, Paragraph):
                        linha_segura.append(cell)
                    else:
                        linha_segura.append(_safe_text(cell))

                linhas_seguras.append(linha_segura)

            if not linhas_seguras:
                return

            tabela = Table(
                linhas_seguras,
                colWidths=col_widths,
                repeatRows=0,
            )

            tabela.setStyle(
                TableStyle(
                    [
                        # =====================================================
                        # FUNDO
                        # =====================================================
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),

                        # =====================================================
                        # BORDAS EXTERNAS
                        # =====================================================
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),

                        # =====================================================
                        # GRID INTERNO
                        # =====================================================
                        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),

                        # =====================================================
                        # ALINHAMENTO
                        # =====================================================
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),

                        # =====================================================
                        # PADDING (RESPONSIVIDADE VISUAL)
                        # =====================================================
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

                        # =====================================================
                        # LINHAS ALTERNADAS (LEITURA)
                        # =====================================================
                        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [
                            colors.white,
                            colors.HexColor("#F8FAFC"),
                        ]),
                    ]
                )
            )

            largura_tabela, altura_tabela = tabela.wrap(largura_util, 10000)

            _garantir_espaco(altura_tabela + 2 * mm)

            tabela.drawOn(
                c,
                margem_esquerda,
                y - altura_tabela,
            )

            y -= altura_tabela + 4 * mm

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

            largura_interna = largura_util - 10 * mm

            alturas: List[float] = []

            for t in textos_validos:
                try:
                    h = _paragraph_height(t, style_texto_livre, largura_interna)
                    if h <= 0:
                        h = 12
                    alturas.append(h)
                except Exception:
                    alturas.append(12)

            # =========================================================
            # ESPAÇAMENTO ENTRE PARÁGRAFOS
            # =========================================================
            espacamento_entre_blocos = 3

            altura_total = (
                sum(alturas)
                + (len(alturas) - 1) * espacamento_entre_blocos
                + 10 * mm
            )

            _garantir_espaco(altura_total)

            # =========================================================
            # FUNDO (LEVEMENTE TÉCNICO, NÃO BRANCO PURO)
            # =========================================================
            c.setFillColor(colors.HexColor("#F8FAFC"))
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(0.7)

            c.roundRect(
                margem_esquerda,
                y - altura_total,
                largura_util,
                altura_total,
                2 * mm,
                stroke=1,
                fill=1,
            )

            # =========================================================
            # LINHA SUPERIOR INTERNA (REFINO VISUAL)
            # =========================================================
            c.setStrokeColor(colors.HexColor("#E2E8F0"))
            c.setLineWidth(0.5)
            c.line(
                margem_esquerda,
                y - 2 * mm,
                margem_esquerda + largura_util,
                y - 2 * mm,
            )

            # =========================================================
            # RENDERIZAÇÃO DOS TEXTOS
            # =========================================================
            y_cursor = y - 5 * mm

            for idx, texto in enumerate(textos_validos):
                try:
                    h = _draw_paragraph(
                        texto,
                        margem_esquerda + 5 * mm,
                        y_cursor,
                        largura_interna,
                        style_texto_livre,
                    )
                except Exception:
                    h = 12

                y_cursor -= h

                # separador leve entre blocos
                if idx < len(textos_validos) - 1:
                    y_cursor -= espacamento_entre_blocos

            y -= altura_total + 4 * mm

        def _draw_table_with_header(
            headers: List[str],
            rows: List[List[str]],
            col_widths: List[float],
        ):
            nonlocal y

            if not headers or not isinstance(headers, list):
                return

            # =========================================================
            # NORMALIZAÇÃO DOS HEADERS
            # =========================================================
            headers_seguro: List[str] = []
            for h in headers:
                try:
                    headers_seguro.append(_safe_text(h))
                except Exception:
                    headers_seguro.append("")

            # =========================================================
            # NORMALIZAÇÃO DAS LINHAS
            # =========================================================
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

            # evita tabela vazia
            data = [headers_seguro] + (rows_seguras or [["" for _ in headers_seguro]])

            tabela = Table(
                data,
                colWidths=col_widths,
                repeatRows=1,
            )

            tabela.setStyle(
                TableStyle(
                    [
                        # =====================================================
                        # HEADER
                        # =====================================================
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 9),

                        # =====================================================
                        # CORPO
                        # =====================================================
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111827")),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 8.5),

                        # =====================================================
                        # BORDAS EXTERNAS
                        # =====================================================
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),

                        # =====================================================
                        # GRID INTERNO (MAIS SUAVE)
                        # =====================================================
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),

                        # =====================================================
                        # ALINHAMENTO
                        # =====================================================
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),

                        # =====================================================
                        # PADDING (MELHOR RESPIRO)
                        # =====================================================
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

                        # =====================================================
                        # LINHAS ALTERNADAS (LEITURA)
                        # =====================================================
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                            colors.white,
                            colors.HexColor("#F8FAFC"),
                        ]),
                    ]
                )
            )

            largura_tabela, altura_tabela = tabela.wrap(largura_util, 10000)

            _garantir_espaco(altura_tabela + 3 * mm)

            tabela.drawOn(
                c,
                margem_esquerda,
                y - altura_tabela,
            )

            y -= altura_tabela + 5 * mm

        def _draw_footer():
            # =========================================================
            # LINHA SUPERIOR (SEPARAÇÃO)
            # =========================================================
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(0.6)

            c.line(
                margem_esquerda,
                20 * mm,
                margem_esquerda + largura_util,
                20 * mm,
            )

            # =========================================================
            # TEXTO INSTITUCIONAL
            # =========================================================
            texto_principal = (
                "GeoINCRA • Sistema de Georreferenciamento e Engenharia Documental"
            )

            texto_secundario = (
                "Documento gerado automaticamente com base em OCR, IA e processamento geoespacial"
            )

            data_emissao = datetime.utcnow().strftime("%d/%m/%Y • %H:%M:%S UTC")

            # =========================================================
            # CONFIGURAÇÃO BASE
            # =========================================================
            c.setFillColor(colors.HexColor("#475569"))

            # =========================================================
            # LINHA 1 (PRINCIPAL)
            # =========================================================
            c.setFont("Helvetica-Bold", 7.5)

            max_width = largura_util - 60 * mm
            texto_final = texto_principal

            while (
                stringWidth(texto_final, "Helvetica-Bold", 7.5) > max_width
                and len(texto_final) > 10
            ):
                texto_final = texto_final[:-1]

            if texto_final != texto_principal:
                texto_final = texto_final.rstrip() + "..."

            c.drawString(
                margem_esquerda,
                15.5 * mm,
                texto_final,
            )

            # =========================================================
            # LINHA 2 (DESCRIÇÃO TÉCNICA)
            # =========================================================
            c.setFont("Helvetica", 7)

            texto_sec = texto_secundario
            while (
                stringWidth(texto_sec, "Helvetica", 7) > max_width
                and len(texto_sec) > 10
            ):
                texto_sec = texto_sec[:-1]

            if texto_sec != texto_secundario:
                texto_sec = texto_sec.rstrip() + "..."

            c.drawString(
                margem_esquerda,
                12.5 * mm,
                texto_sec,
            )

            # =========================================================
            # DATA (DIREITA)
            # =========================================================
            c.setFont("Helvetica", 7.5)

            c.drawRightString(
                margem_esquerda + largura_util,
                14 * mm,
                data_emissao,
            )

        # =========================================================
        # NORMALIZAÇÃO DOS DADOS DE ENTRADA (UPGRADE PROFISSIONAL)
        # =========================================================

        def _safe_num(valor: Any) -> Optional[float]:
            try:
                if valor is None:
                    return None
                texto = str(valor).replace(",", ".")
                return float(texto)
            except Exception:
                return None

        def _safe_str(valor: Any) -> Optional[str]:
            return _safe_text(valor)

        matricula_obj = (
            dados.get("matricula")
            if isinstance(dados.get("matricula"), dict)
            else {}
        )

        numero_matricula = _safe_str(
            dados.get("numero_matricula")
            or matricula_obj.get("numero")
            or dados.get("matricula")
            or dados.get("numero")
        )

        comarca = _safe_str(
            dados.get("comarca")
            or matricula_obj.get("comarca")
        )

        livro = _safe_str(
            dados.get("livro")
            or matricula_obj.get("livro")
        )

        folha = _safe_str(
            dados.get("folha")
            or matricula_obj.get("folha")
        )

        codigo_cartorio = _safe_str(
            dados.get("codigo_cartorio")
        )

        status = _safe_str(
            dados.get("status") or "ATIVA"
        )

        # =========================================================
        # 🔥 IMÓVEL (REFORÇADO)
        # =========================================================

        descricao_imovel = _safe_str(
            dados.get("descricao_imovel")
            or (dados.get("imovel") or {}).get("descricao")
            or dados.get("nome_imovel")
        )

        municipio = _safe_str(
            dados.get("municipio")
            or (dados.get("imovel") or {}).get("municipio")
        )

        # =========================================================
        # 🔥 ÁREA (PADRÃO PROFISSIONAL)
        # =========================================================

        area_total_raw = dados.get("area_total")
        unidade_area = _safe_str(dados.get("unidade_area"))
        area_hectares_raw = dados.get("area_hectares")

        area_hectares = _safe_num(area_hectares_raw)
        area_total = _safe_num(area_total_raw)

        area_formatada = None

        if area_hectares:
            try:
                area_formatada = (
                    f"{area_hectares:,.4f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                    + " ha"
                )
            except Exception:
                area_formatada = f"{area_hectares} ha"

        elif area_total and unidade_area:
            try:
                valor_fmt = (
                    f"{area_total:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                area_formatada = f"{valor_fmt} {unidade_area}"
            except Exception:
                area_formatada = f"{area_total} {unidade_area}"

        # =========================================================
        # 🔥 DESCRIÇÃO FINAL DO IMÓVEL (ENRIQUECIDA)
        # =========================================================

        if descricao_imovel and municipio:
            descricao_imovel_final = f"{descricao_imovel} - {municipio}"
        else:
            descricao_imovel_final = descricao_imovel or municipio

        # =========================================================
        # 🔥 MEMORIAL / GEOMETRIA (ROBUSTO)
        # =========================================================

        memorial_texto = _safe_text(
            dados.get("memorial_texto")
            or dados.get("memorial")
            or dados.get("inteiro_teor")
        )

        possui_memorial = bool(memorial_texto and len(memorial_texto) > 20)

        # =========================================================
        # 🔥 GEOJSON (VALIDAÇÃO REAL)
        # =========================================================

        geojson = dados.get("geojson")

        possui_geo = (
            isinstance(geojson, dict)
            and bool(geojson.get("coordinates"))
        )

        # =========================================================
        # 🔥 LISTAS NORMALIZADAS (COM LIMPEZA)
        # =========================================================

        confrontantes_raw = dados.get("confrontantes") or []
        proprietarios_raw = dados.get("proprietarios") or []

        confrontantes = []
        proprietarios = []

        if isinstance(confrontantes_raw, list):
            for item in confrontantes_raw:
                if isinstance(item, dict) and any(item.values()):
                    confrontantes.append(item)

        if isinstance(proprietarios_raw, list):
            for item in proprietarios_raw:
                if isinstance(item, dict) and any(item.values()):
                    proprietarios.append(item)

        # =========================================================
        # PÁGINA
        # =========================================================

        _draw_page_frame()
        _draw_header_principal()

        # =========================================================
        # SEÇÃO — IDENTIFICAÇÃO DA MATRÍCULA
        # =========================================================

        _draw_section_title("1. IDENTIFICAÇÃO DA MATRÍCULA")

        numero_matricula_fmt = numero_matricula or "NÃO INFORMADO"
        comarca_fmt = comarca or "NÃO INFORMADO"
        livro_fmt = livro or "NÃO INFORMADO"
        folha_fmt = folha or "NÃO INFORMADO"
        codigo_cartorio_fmt = codigo_cartorio or "NÃO INFORMADO"
        status_fmt = (status or "NÃO INFORMADO").upper()
        area_fmt = area_formatada or "NÃO INFORMADO"

        info_linhas = [
            [
                Paragraph("<b>Número da Matrícula</b>", style_bloco_bold),
                Paragraph(numero_matricula_fmt, style_bloco),
                Paragraph("<b>Comarca</b>", style_bloco_bold),
                Paragraph(comarca_fmt, style_bloco),
            ],
            [
                Paragraph("<b>Livro</b>", style_bloco_bold),
                Paragraph(livro_fmt, style_bloco),
                Paragraph("<b>Folha</b>", style_bloco_bold),
                Paragraph(folha_fmt, style_bloco),
            ],
            [
                Paragraph("<b>Código do Cartório</b>", style_bloco_bold),
                Paragraph(codigo_cartorio_fmt, style_bloco),
                Paragraph("<b>Status</b>", style_bloco_bold),
                Paragraph(status_fmt, style_bloco),
            ],
            [
                Paragraph("<b>Área do Imóvel</b>", style_bloco_bold),
                Paragraph(area_fmt, style_bloco),
                Paragraph("<b>Tipo de Registro</b>", style_bloco_bold),
                Paragraph("RURAL", style_bloco),
            ],
        ]

        _draw_info_table(
            linhas=info_linhas,
            col_widths=[
                36 * mm,
                54 * mm,
                36 * mm,
                largura_util - (36 * mm + 54 * mm + 36 * mm),
            ],
        )

        # =========================================================
        # 🔥 SEÇÃO — IDENTIFICAÇÃO DO IMÓVEL (REFINADA)
        # =========================================================
        _draw_section_title("2. IDENTIFICAÇÃO DO IMÓVEL")

        textos_imovel: List[str] = []

        descricao_fmt = descricao_imovel_final or "NÃO INFORMADO"

        textos_imovel.append(f"<b>Descrição do imóvel:</b> {descricao_fmt}")

        # =========================================================
        # ÁREA ORIGINAL (COMO VEIO DO DOCUMENTO)
        # =========================================================
        if area_total and unidade_area:
            try:
                valor_original = (
                    f"{float(area_total):,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                textos_imovel.append(
                    f"<b>Área constante na matrícula:</b> {valor_original} {unidade_area}"
                )
            except Exception:
                textos_imovel.append(
                    "<b>Área constante na matrícula:</b> NÃO INFORMADO"
                )

        # =========================================================
        # ÁREA OFICIAL (PADRONIZADA EM HECTARES)
        # =========================================================
        if area_formatada:
            textos_imovel.append(
                f"<b>Área oficial georreferenciada:</b> {area_formatada}"
            )

        # =========================================================
        # FALLBACK SE NÃO HOUVER DADOS
        # =========================================================
        if textos_imovel:
            _draw_text_box(textos_imovel)
        else:
            _draw_text_box(
                [
                    "Não foi possível identificar dados técnicos suficientes do imóvel para composição desta seção."
                ]
            )

        # =========================================================
        # SEÇÃO — PROPRIETÁRIOS (REFINADA)
        # =========================================================
        _draw_section_title("3. PROPRIETÁRIOS")

        proprietarios_rows: List[List[str]] = []

        def _formatar_cpf_cnpj(valor: Optional[str]) -> Optional[str]:
            if not valor:
                return None

            texto = "".join(filter(str.isdigit, str(valor)))

            if len(texto) == 11:
                return f"{texto[:3]}.{texto[3:6]}.{texto[6:9]}-{texto[9:]}"
            elif len(texto) == 14:
                return f"{texto[:2]}.{texto[2:5]}.{texto[5:8]}/{texto[8:12]}-{texto[12:]}"
            return valor

        if proprietarios:
            for idx, p in enumerate(proprietarios, start=1):

                if not isinstance(p, dict):
                    continue

                nome = _safe_text(p.get("nome"))
                cpf_cnpj_raw = _safe_text(p.get("cpf_cnpj"))
                cpf_cnpj = _formatar_cpf_cnpj(cpf_cnpj_raw)

                tipo_raw = str(p.get("tipo") or "").upper().strip()

                # =========================================================
                # NORMALIZAÇÃO PROFISSIONAL DO TIPO
                # =========================================================
                if tipo_raw in ["PF", "FISICA", "PESSOA FISICA"]:
                    tipo = "Pessoa Física"
                elif tipo_raw in ["PJ", "JURIDICA", "PESSOA JURIDICA"]:
                    tipo = "Pessoa Jurídica"
                else:
                    # inferência automática se possível
                    if cpf_cnpj and len("".join(filter(str.isdigit, cpf_cnpj))) == 11:
                        tipo = "Pessoa Física"
                    elif cpf_cnpj and len("".join(filter(str.isdigit, cpf_cnpj))) == 14:
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
                headers=["#", "Nome / Razão Social", "CPF/CNPJ", "Tipo"],
                rows=proprietarios_rows,
                col_widths=[
                    10 * mm,
                    80 * mm,
                    45 * mm,
                    largura_util - (10 * mm + 80 * mm + 45 * mm),
                ],
            )
        else:
            _draw_text_box(
                [
                    "Não foram identificados proprietários válidos para composição desta matrícula técnica."
                ]
            )

        # =========================================================
        # SEÇÃO — CONFRONTANTES (REFINADO NÍVEL TÉCNICO)
        # =========================================================
        _draw_section_title("4. CONFRONTANTES")

        style_confrontante = ParagraphStyle(
            name="Confrontante",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            wordWrap="CJK",
        )

        def _truncate_text(texto: str, limite: int = 180) -> str:
            if not texto:
                return "NÃO INFORMADO"

            texto = " ".join(str(texto).split())

            if len(texto) > limite:
                return texto[:limite].rstrip() + "..."

            return texto

        def _normalizar_direcao(valor: str | None) -> str:
            if not valor:
                return "NÃO INFORMADO"

            texto = str(valor).upper().strip()

            mapa = {
                "N": "NORTE",
                "S": "SUL",
                "E": "LESTE",
                "W": "OESTE",
                "NE": "NORDESTE",
                "NW": "NOROESTE",
                "SE": "SUDESTE",
                "SW": "SUDOESTE",
            }

            if texto in mapa:
                return mapa[texto]

            return texto

        confrontantes_rows: List[List[Any]] = []

        if confrontantes:
            for idx, cft in enumerate(confrontantes, start=1):

                if not isinstance(cft, dict):
                    continue

                # =========================================================
                # DIREÇÃO
                # =========================================================
                direcao_raw = (
                    cft.get("lado_normalizado")
                    or cft.get("direcao")
                    or cft.get("lado")
                )

                direcao = _normalizar_direcao(_safe_text(direcao_raw))

                # =========================================================
                # DADOS BASE
                # =========================================================
                nome = _safe_text(cft.get("nome"))
                matricula_cft = _safe_text(cft.get("matricula"))
                identificacao = _safe_text(cft.get("identificacao"))
                descricao = _safe_text(cft.get("descricao"))

                tipo = _safe_text(cft.get("tipo"))
                lote = _safe_text(cft.get("lote"))
                gleba = _safe_text(cft.get("gleba"))

                # =========================================================
                # FILTRO
                # =========================================================
                if not any([nome, matricula_cft, identificacao, descricao]):
                    continue

                # =========================================================
                # TEXTO BASE (PRIORIDADE JURÍDICA)
                # =========================================================
                texto_base = (
                    nome
                    or identificacao
                    or (f"MATRÍCULA {matricula_cft}" if matricula_cft else None)
                    or descricao
                    or "CONFRONTANTE NÃO IDENTIFICADO"
                )

                # =========================================================
                # DESCRIÇÃO TÉCNICA ESTRUTURADA
                # =========================================================
                partes: List[str] = []

                if matricula_cft:
                    partes.append(f"Matrícula: {matricula_cft}")

                if identificacao:
                    partes.append(f"Imóvel: {identificacao}")

                if lote:
                    partes.append(f"Lote: {lote}")

                if gleba:
                    partes.append(f"Gleba: {gleba}")

                if tipo:
                    partes.append(f"Tipo: {tipo}")

                if descricao:
                    partes.append(descricao)

                if not partes:
                    partes.append(texto_base)

                descricao_composta = _truncate_text(
                    " | ".join(partes),
                    limite=180,
                )

                # =========================================================
                # LINHA FINAL
                # =========================================================
                confrontantes_rows.append(
                    [
                        Paragraph(str(idx), style_confrontante),
                        Paragraph(direcao, style_confrontante),
                        Paragraph(_truncate_text(texto_base, 80), style_confrontante),
                        Paragraph(descricao_composta, style_confrontante),
                    ]
                )

        # =========================================================
        # RENDERIZAÇÃO DA TABELA
        # =========================================================
        if confrontantes_rows:
            _draw_table_with_header(
                headers=["#", "Direção", "Confrontante", "Detalhamento Técnico"],
                rows=confrontantes_rows,
                col_widths=[
                    10 * mm,
                    20 * mm,
                    45 * mm,
                    largura_util - (10 * mm + 20 * mm + 45 * mm),
                ],
            )
        else:
            _draw_text_box(
                [
                    "Não foram identificados confrontantes válidos para composição desta matrícula técnica."
                ]
            )

        # =========================================================
        # 🔥 ANÁLISE JURÍDICA (REFINADA)
        # =========================================================
        try:
            from app.services.matricula_analysis_service import MatriculaAnalysisService

            # =========================================================
            # TEXTO BASE (PRIORIDADE INTELIGENTE)
            # =========================================================
            texto_base = (
                dados.get("inteiro_teor")
                or dados.get("memorial_texto")
                or dados.get("descricao_imovel")
                or ""
            )

            texto_base = _safe_text(texto_base) or ""

            analise = MatriculaAnalysisService.analisar(
                texto=texto_base,
            ) or {}

            _draw_section_title("5. ANÁLISE JURÍDICA E HISTÓRICO REGISTRAL")

            blocos_analise: List[str] = []

            classificacao = analise.get("classificacao") or {}

            status_raw = classificacao.get("status")
            status_fmt = _safe_upper(status_raw) or "NÃO DEFINIDO"

            try:
                score = int(analise.get("score_juridico") or 0)
            except Exception:
                score = 0

            # =========================================================
            # CABEÇALHO DA ANÁLISE
            # =========================================================
            blocos_analise.append(f"<b>Status jurídico:</b> {status_fmt}")
            blocos_analise.append(f"<b>Score jurídico:</b> {score} / 100")

            # =========================================================
            # REGISTROS / AVERBAÇÕES
            # =========================================================
            registros = analise.get("registros") or []
            averbacoes = analise.get("averbacoes") or []

            if registros or averbacoes:
                blocos_analise.append("<b>Atos registrais identificados:</b>")

                for r in registros[:8]:
                    r_safe = _safe_text(r)
                    if r_safe:
                        blocos_analise.append(f"- Registro: {r_safe}")

                for a in averbacoes[:8]:
                    a_safe = _safe_text(a)
                    if a_safe:
                        blocos_analise.append(f"- Averbação: {a_safe}")

            # =========================================================
            # ÔNUS
            # =========================================================
            onus = analise.get("onus") or []

            if onus:
                blocos_analise.append("<b>Ônus identificados:</b>")
                for o in onus[:8]:
                    o_safe = _safe_text(o)
                    if o_safe:
                        blocos_analise.append(f"- {o_safe}")

            # =========================================================
            # RISCOS
            # =========================================================
            riscos = analise.get("riscos") or []

            if riscos:
                blocos_analise.append("<b>Riscos jurídicos:</b>")
                for r in riscos[:8]:
                    r_safe = _safe_text(r)
                    if r_safe:
                        blocos_analise.append(f"- {r_safe}")

            # =========================================================
            # ENRIQUECIMENTO OCR
            # =========================================================
            proprietarios_ocr = dados.get("proprietarios") or []
            confrontantes_ocr = dados.get("confrontantes") or []

            if isinstance(proprietarios_ocr, list) and proprietarios_ocr:
                blocos_analise.append("<b>Proprietários identificados via OCR:</b>")
                blocos_analise.append(f"- Total: {len(proprietarios_ocr)}")

            if isinstance(confrontantes_ocr, list) and confrontantes_ocr:
                blocos_analise.append("<b>Confrontantes identificados:</b>")
                blocos_analise.append(f"- Total: {len(confrontantes_ocr)}")

            # =========================================================
            # FALLBACK
            # =========================================================
            if not blocos_analise:
                blocos_analise.append(
                    "Nenhuma informação jurídica relevante foi identificada a partir do documento analisado."
                )

            _draw_text_box(blocos_analise)

        except Exception as exc:
            _draw_text_box(
                [
                    "Não foi possível gerar a análise jurídica deste documento.",
                    f"Detalhes técnicos: {str(exc)}"
                ]
            )

        # =========================================================
        # 🔥 MEMORIAL DESCRITIVO (REFINADO)
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

                geojson_valido = (
                    isinstance(geojson, dict)
                    and bool(geojson.get("coordinates"))
                )

                if geojson_valido:
                    txt_vertices = TxtLispService.gerar_txt(geojson)

                    linhas = txt_vertices.split("\n")

                    # 🔥 filtra apenas vértices válidos
                    linhas_vertices = [
                        l.strip()
                        for l in linhas
                        if l.strip().startswith("V")
                    ]

                    # 🔥 limite de segurança (evita PDF gigante)
                    linhas_vertices = linhas_vertices[:120]

                    if linhas_vertices:
                        bloco_vertices = "\n".join(linhas_vertices)

                        memorial_final += (
                            "\n\n"
                            "------------------------------------------------------------\n"
                            "COORDENADAS DOS VÉRTICES (FORMATO TÉCNICO):\n\n"
                            f"{bloco_vertices}\n"
                            "------------------------------------------------------------"
                        )

            except Exception as e:
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
        # SEÇÃO — OBSERVAÇÃO TÉCNICA (REFINADA)
        # =========================================================
        _draw_section_title("7. OBSERVAÇÃO TÉCNICA")

        observacoes_bloco: List[str] = []

        # =========================================================
        # CONTEXTO DA MATRÍCULA
        # =========================================================
        if numero_matricula:
            observacoes_bloco.append(
                f"Matrícula de referência analisada: <b>{numero_matricula}</b>."
            )

        # =========================================================
        # DESCRIÇÃO DO PROCESSAMENTO
        # =========================================================
        observacoes_bloco.append(
            (
                "Este documento foi gerado automaticamente pelo sistema GeoINCRA, "
                "por meio de pipeline técnico composto por leitura OCR, interpretação "
                "assistida por inteligência artificial e processamento estruturado "
                "das informações extraídas da matrícula imobiliária."
            )
        )

        # =========================================================
        # CARÁTER DO DOCUMENTO
        # =========================================================
        observacoes_bloco.append(
            (
                "As informações apresentadas possuem caráter técnico-informativo, "
                "sendo destinadas ao apoio em análises preliminares, levantamentos "
                "e organização documental do imóvel."
            )
        )

        # =========================================================
        # RESPONSABILIDADE PROFISSIONAL
        # =========================================================
        observacoes_bloco.append(
            (
                "A utilização deste documento para fins legais, registrais, "
                "cartoriais ou judiciais deverá ser precedida de validação por "
                "profissional legalmente habilitado, conforme legislação vigente."
            )
        )

        # =========================================================
        # LIMITAÇÕES DO OCR / IA
        # =========================================================
        observacoes_bloco.append(
            (
                "Por se tratar de processamento automatizado, podem existir "
                "limitações decorrentes da qualidade do documento original, "
                "formatação da matrícula ou ambiguidades textuais, sendo "
                "recomendável conferência manual das informações críticas."
            )
        )

        # =========================================================
        # RASTREABILIDADE
        # =========================================================
        observacoes_bloco.append(
            (
                "Todas as informações aqui consolidadas estão vinculadas aos dados "
                "processados no momento da geração deste documento, garantindo "
                "rastreabilidade técnica dentro do sistema GeoINCRA."
            )
        )

        _draw_text_box(observacoes_bloco)

        # =========================================================
        # 🔥 CROQUI DO IMÓVEL (REFINADO)
        # =========================================================
        if possui_geo:

            croqui_path = None

            try:
                croqui_path = MatriculaPdfService._gerar_croqui_png(imovel_id, dados)
            except Exception:
                croqui_path = None

            croqui_valido = (
                croqui_path
                and isinstance(croqui_path, str)
                and os.path.exists(croqui_path)
            )

            if croqui_valido:

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

                except Exception as e:
                    _draw_text_box(
                        [
                            "Não foi possível renderizar o croqui do imóvel.",
                            f"Detalhe técnico: {str(e)}"
                        ]
                    )

            else:
                _draw_text_box(
                    [
                        "Croqui não disponível para este imóvel.",
                        "A geometria pode não ter sido gerada ou validada corretamente no pipeline técnico."
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
            raise Exception(f"[PDF ERROR] Falha ao finalizar documento: {str(e)}")

        # =========================================================
        # URL FINAL (ROBUSTA)
        # =========================================================
        try:
            caminho_relativo = caminho.replace("app/", "") if "app/" in caminho else caminho
            caminho_relativo = caminho_relativo.replace("\\", "/")
        except Exception:
            caminho_relativo = caminho

        url = f"{MatriculaPdfService.BASE_URL}/{caminho_relativo}"

        return {
            "arquivo_path": caminho,
            "arquivo_url": url,
        }