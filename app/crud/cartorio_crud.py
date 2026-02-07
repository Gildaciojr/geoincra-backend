from sqlalchemy.orm import Session
from app.models.cartorio import Cartorio
from app.schemas.cartorio import CartorioCreate, CartorioUpdate


def create_cartorio(db: Session, data: CartorioCreate):
    cartorio = Cartorio(
        nome=data.nome,
        tipo=data.tipo,
        municipio=data.municipio,
        estado=data.estado,
        telefone=data.telefone,
        email=data.email,
        endereco=data.endereco,
        cns=data.cns,
        comarca=data.comarca,
    )
    db.add(cartorio)
    db.commit()
    db.refresh(cartorio)
    return cartorio


def list_cartorios(db: Session):
    return (
        db.query(Cartorio)
        .order_by(
            Cartorio.estado.asc(),
            Cartorio.municipio.asc(),
            Cartorio.nome.asc(),
        )
        .all()
    )


def get_cartorio(db: Session, cartorio_id: int):
    return db.query(Cartorio).filter(Cartorio.id == cartorio_id).first()


def update_cartorio(db: Session, cartorio_id: int, data: CartorioUpdate):
    cartorio = get_cartorio(db, cartorio_id)
    if not cartorio:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(cartorio, field, value)

    db.commit()
    db.refresh(cartorio)
    return cartorio


def delete_cartorio(db: Session, cartorio_id: int):
    cartorio = get_cartorio(db, cartorio_id)
    if not cartorio:
        return False

    db.delete(cartorio)
    db.commit()
    return True
