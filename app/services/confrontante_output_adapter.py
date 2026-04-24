from __future__ import annotations

from typing import List, Dict, Optional

from app.models.confrontante import Confrontante


class ConfrontanteOutputAdapter:

    @staticmethod
    def _safe_text(valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None

        texto = str(valor).strip()
        if not texto:
            return None

        return " ".join(texto.split())

    @staticmethod
    def from_models(confrontantes: List[Confrontante]) -> List[Dict]:

        if not confrontantes:
            return []

        resultado: List[Dict] = []

        for c in confrontantes:

            nome = ConfrontanteOutputAdapter._safe_text(c.nome_confrontante)
            descricao = ConfrontanteOutputAdapter._safe_text(c.descricao)
            identificacao = ConfrontanteOutputAdapter._safe_text(
                c.identificacao_imovel_confrontante
            )
            matricula = ConfrontanteOutputAdapter._safe_text(
                c.matricula_confrontante
            )

            # 🔥 fallback inteligente REAL (nível técnico)
            texto_base = (
                nome
                or identificacao
                or descricao
                or (f"MATRÍCULA {matricula}" if matricula else None)
                or "CONFRONTANTE NÃO IDENTIFICADO"
            )

            resultado.append({
                # =====================================================
                # GEOMETRIA
                # =====================================================
                "ordem_segmento": c.ordem_segmento,
                "lado": c.lado_label,
                "lado_normalizado": c.direcao_normalizada,
                "direcao": c.direcao_normalizada,

                # =====================================================
                # IDENTIFICAÇÃO
                # =====================================================
                "nome": nome,
                "descricao": descricao or texto_base,
                "identificacao": identificacao,
                "matricula": matricula,

                # =====================================================
                # DADOS AGRÁRIOS (🔥 AGORA NÃO PERDE)
                # =====================================================
                "lote": getattr(c, "lote", None),
                "gleba": getattr(c, "gleba", None),

                # =====================================================
                # TIPO
                # =====================================================
                "tipo": getattr(c, "tipo", None),

                # =====================================================
                # TEXTO FINAL CONSOLIDADO
                # =====================================================
                "texto_resumo": texto_base,
            })

        # 🔥 ordenação crítica (NÃO ALTERAR)
        resultado.sort(
            key=lambda x: (
                x["ordem_segmento"] if x["ordem_segmento"] is not None else 9999
            )
        )

        return resultado