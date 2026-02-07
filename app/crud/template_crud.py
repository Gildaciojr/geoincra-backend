from sqlalchemy.orm import Session
from app.models.template import Template
from app.schemas.template import TemplateCreate


def create_template(db: Session, data: TemplateCreate) -> Template:
    obj = Template(
        nome=data.nome,
        descricao=data.descricao,
        categoria=data.categoria,
        versao=data.versao,
        stored_filename=data.stored_filename,
        original_filename=data.original_filename,
        file_path=data.file_path,
        ativo=True,  # explícito para robustez SaaS
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_templates(db: Session, categoria: str | None = None):
    query = db.query(Template).filter(Template.ativo.is_(True))

    if categoria:
        query = query.filter(Template.categoria == categoria)

    return query.order_by(Template.nome.asc()).all()


def get_template(db: Session, template_id: int) -> Template | None:
    return db.query(Template).filter(Template.id == template_id).first()
