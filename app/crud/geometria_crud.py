from sqlalchemy.orm import Session
from app.models.geometria import Geometria
from app.schemas.geometria import GeometriaCreate, GeometriaUpdate
from app.services.geometria_service import GeometriaService


def create_geometria(db: Session, imovel_id: int, data: GeometriaCreate) -> Geometria:
    epsg_utm, area_ha, perimetro_m = GeometriaService.calcular_area_perimetro(
        geojson=data.geojson,
        epsg_origem=data.epsg_origem,
    )

    obj = Geometria(
        imovel_id=imovel_id,
        nome=data.nome,
        observacoes=data.observacoes,
        geojson=data.geojson,
        epsg_origem=data.epsg_origem,
        epsg_utm=epsg_utm,
        area_hectares=area_ha,
        perimetro_m=perimetro_m,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_geometrias(db: Session, imovel_id: int) -> list[Geometria]:
    return (
        db.query(Geometria)
        .filter(Geometria.imovel_id == imovel_id)
        .order_by(Geometria.created_at.desc())
        .all()
    )


def get_geometria(db: Session, geometria_id: int) -> Geometria | None:
    return db.query(Geometria).filter(Geometria.id == geometria_id).first()


def update_geometria(db: Session, geometria_id: int, data: GeometriaUpdate) -> Geometria | None:
    obj = get_geometria(db, geometria_id)
    if not obj:
        return None

    payload = data.model_dump(exclude_unset=True)

    # Se atualizar geojson/epsg -> recalcula
    geojson_new = payload.get("geojson", None)
    epsg_new = payload.get("epsg_origem", None)

    if geojson_new is not None:
        obj.geojson = geojson_new

    if epsg_new is not None:
        obj.epsg_origem = epsg_new

    if geojson_new is not None or epsg_new is not None:
        epsg_utm, area_ha, perimetro_m = GeometriaService.calcular_area_perimetro(
            geojson=obj.geojson,
            epsg_origem=obj.epsg_origem,
        )
        obj.epsg_utm = epsg_utm
        obj.area_hectares = area_ha
        obj.perimetro_m = perimetro_m

    if "nome" in payload:
        obj.nome = payload["nome"]
    if "observacoes" in payload:
        obj.observacoes = payload["observacoes"]

    db.commit()
    db.refresh(obj)
    return obj


def delete_geometria(db: Session, geometria_id: int) -> bool:
    obj = get_geometria(db, geometria_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
