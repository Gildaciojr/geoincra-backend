from __future__ import annotations

from typing import List, Dict

from app.models.confrontante import Confrontante


class ConfrontanteOutputAdapter:

    @staticmethod
    def from_models(confrontantes: List[Confrontante]) -> List[Dict]:
        if not confrontantes:
            return []

        resultado: List[Dict] = []

        for c in confrontantes:

            nome = c.nome_confrontante
            descricao = c.descricao
            identificacao = c.identificacao_imovel_confrontante

            # 🔥 fallback inteligente
            texto_base = nome or descricao or identificacao or "CONFRONTANTE NÃO IDENTIFICADO"

            resultado.append({
                "ordem_segmento": c.ordem_segmento,
                "lado_normalizado": c.direcao_normalizada,
                "nome": nome,
                "descricao": descricao or texto_base,
                "lote": None,
                "gleba": None,
            })

        # 🔥 ordenação crítica
        resultado.sort(key=lambda x: (x["ordem_segmento"] or 9999))

        return resultado