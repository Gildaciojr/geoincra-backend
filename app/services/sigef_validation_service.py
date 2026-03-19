# app/services/sigef_validation_service.py

from __future__ import annotations

import json
from typing import Any, Dict, List

from shapely.geometry import shape, Polygon


class SigefValidationService:

    @staticmethod
    def validar(geojson: str) -> Dict[str, Any]:
        result = {
            "valido": True,
            "score": 1.0,
            "errors": [],
            "warnings": [],
            "checks": {},
        }

        try:
            geom = shape(json.loads(geojson))
        except Exception:
            return {
                "valido": False,
                "score": 0,
                "errors": ["GeoJSON inválido"],
                "warnings": [],
                "checks": {},
            }

        if not isinstance(geom, Polygon):
            result["errors"].append("Geometria não é polígono")
            result["valido"] = False
            return result

        coords = list(geom.exterior.coords)

        # =========================================
        # 1. FECHAMENTO
        # =========================================
        fechado = coords[0] == coords[-1]
        result["checks"]["fechamento"] = fechado

        if not fechado:
            result["errors"].append("Polígono não está fechado")
            result["valido"] = False

        # =========================================
        # 2. AUTO-INTERSEÇÃO
        # =========================================
        if not geom.is_valid:
            result["errors"].append("Geometria possui auto-interseção")
            result["valido"] = False

        # =========================================
        # 3. ORIENTAÇÃO (SIGEF espera anti-horário)
        # =========================================
        if geom.exterior.is_ccw is False:
            result["warnings"].append("Polígono não está no sentido anti-horário")

        # =========================================
        # 4. VÉRTICES DUPLICADOS
        # =========================================
        unique = set(coords)
        if len(unique) != len(coords):
            result["warnings"].append("Existem vértices duplicados")

        # =========================================
        # 5. DISTÂNCIAS MÍNIMAS
        # =========================================
        dist_zero = False
        for i in range(len(coords) - 1):
            if coords[i] == coords[i + 1]:
                dist_zero = True
                break

        if dist_zero:
            result["errors"].append("Segmentos com distância zero")
            result["valido"] = False

        # =========================================
        # SCORE
        # =========================================
        penalty = (len(result["errors"]) * 0.3) + (len(result["warnings"]) * 0.1)
        result["score"] = max(0.0, 1.0 - penalty)

        return result