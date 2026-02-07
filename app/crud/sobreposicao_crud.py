# app/crud/sobreposicao_crud.py

from sqlalchemy.orm import Session
from app.models.sobreposicao import Sobreposicao
from app.models.geometria import Geometria
from app.services.geometria_service import GeometriaService
from app.services.sobreposicao_service import SobreposicaoService


def analisar_sobreposicao(
    db: Session,
    geometria_base_id: int,
    geometria_afetada_id: int,
    tipo: str,
):
    base = db.query(Geometria).get(geometria_base_id)
    afetada = db.query(Geometria).get(geometria_afetada_id)

    if not base or not afetada:
        return None

    resultado = SobreposicaoService.calcular(
        base.geojson,
        afetada.geojson,
    )

    if not resultado:
        return None

    # Converter interseção para hectares reais (UTM)
    intersecao_geojson = base.geojson

    calculo = GeometriaService.calcular_area_perimetro(intersecao_geojson)

    area_ha = calculo["area_hectares"]

    percentual = (area_ha / base.area_hectares) * 100

    obj = Sobreposicao(
        geometria_base_id=geometria_base_id,
        geometria_afetada_id=geometria_afetada_id,
        area_sobreposta_ha=area_ha,
        percentual_sobreposicao=percentual,
        tipo=tipo,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
