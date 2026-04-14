from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.geometria_service import GeometriaService


class GeometriaPersistenciaService:

    @staticmethod
    def persistir_estrutura(
        db: Session,
        geometria_id: int,
        geojson
    ) -> None:

        if not geometria_id or not geojson:
            return

        # =========================================================
        # 🔥 LIMPEZA PRÉVIA (IDEMPOTÊNCIA)
        # =========================================================
        db.execute(
            "DELETE FROM segmentos WHERE geometria_id = :gid",
            {"gid": geometria_id}
        )

        db.execute(
            "DELETE FROM vertices WHERE geometria_id = :gid",
            {"gid": geometria_id}
        )

        # =========================================================
        # 🔥 EXTRAÇÃO DE ENGENHARIA
        # =========================================================
        segmentos = GeometriaService.extract_segmentos(geojson)

        if not segmentos:
            return

        # =========================================================
        # 🔥 INSERÇÃO DE VÉRTICES
        # =========================================================
        vertices_ids = []

        for seg in segmentos:
            result = db.execute(
                """
                INSERT INTO vertices (geometria_id, indice, x, y)
                VALUES (:gid, :indice, :x, :y)
                RETURNING id
                """,
                {
                    "gid": geometria_id,
                    "indice": seg["indice"],
                    "x": float(seg["ponto_inicial"]["x"]),
                    "y": float(seg["ponto_inicial"]["y"]),
                }
            )

            vertex_id = result.fetchone()[0]
            vertices_ids.append(vertex_id)

        # =========================================================
        # 🔥 INSERÇÃO DE SEGMENTOS
        # =========================================================
        for seg in segmentos:
            db.execute(
                """
                INSERT INTO segmentos (
                    geometria_id,
                    indice,
                    distancia,
                    azimute
                )
                VALUES (:gid, :indice, :dist, :az)
                """,
                {
                    "gid": geometria_id,
                    "indice": seg["indice"],
                    "dist": float(seg["distancia"]),
                    "az": float(seg["azimute_graus"]),
                }
            )