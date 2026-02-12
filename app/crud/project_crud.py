from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.models.proprietario import Proprietario

from app.schemas.project_status import ProjectStatusCreate
from app.crud.project_status_crud import definir_status_projeto


def create_project(db: Session, payload: ProjectCreate, owner_id: int):
    try:
        # ===================================
        # 1️⃣ PROJETO
        # ===================================
        project = Project(
            name=payload.name,
            descricao_simplificada=payload.descricao_simplificada,
            tipo_processo=payload.tipo_processo,
            municipio=payload.municipio,
            uf=payload.uf,
            codigo_imovel_rural=payload.codigo_imovel_rural,
            codigo_sncr=payload.codigo_sncr,
            codigo_car=payload.codigo_car,
            codigo_sigef=payload.codigo_sigef,
            observacoes=payload.observacoes,
            owner_id=owner_id,
            status="CADASTRADO",  # snapshot imediato
        )

        db.add(project)
        db.flush()

        # ===================================
        # 2️⃣ IMÓVEL
        # ===================================
        imovel = Imovel(
            project_id=project.id,
            municipio_id=payload.municipio_id,
            area_hectares=payload.area_hectares,
            ccir=payload.ccir,
            matricula_principal=payload.matricula_principal,
            nome=payload.name,
        )

        db.add(imovel)
        db.flush()

        # ===================================
        # 3️⃣ MATRÍCULA PRINCIPAL
        # ===================================
        if payload.matricula_principal:
            matricula = Matricula(
                imovel_id=imovel.id,
                numero_matricula=payload.matricula_principal,
                status="ATIVA",
            )
            db.add(matricula)

        # ===================================
        # 4️⃣ PROPRIETÁRIO
        # ===================================
        proprietario = Proprietario(
            imovel_id=imovel.id,
            nome_completo=payload.proprietario_nome,
            tipo_pessoa=payload.proprietario_tipo,
            cpf=payload.proprietario_cpf,
            cnpj=payload.proprietario_cnpj,
        )
        db.add(proprietario)

        # ===================================
        # 5️⃣ STATUS INICIAL (HISTÓRICO)
        # ===================================
        from app.schemas.project_status import ProjectStatusCreate
        from app.crud.project_status_crud import definir_status_projeto

        definir_status_projeto(
            db=db,
            project_id=project.id,
            data=ProjectStatusCreate(
                status="CADASTRADO",
                descricao="Projeto criado no sistema.",
                definido_automaticamente=True,
                definido_por_usuario_id=None,
            ),
        )

        db.commit()
        db.refresh(project)

        return project

    except Exception:
        db.rollback()
        raise



def list_projects(db: Session, owner_id: int):
    return db.query(Project).filter(Project.owner_id == owner_id).all()


def list_projects_card(db: Session, owner_id: int):
    projects = (
        db.query(Project)
        .filter(Project.owner_id == owner_id)
        .all()
    )

    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "municipio": p.municipio,
            "uf": p.uf,
            "status": p.status,
            "created_at": p.created_at,
            "total_documents": len(p.documents),
            "total_proposals": len(p.proposals),
        })

    return result


def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id).first()


def update_project(db: Session, project_id: int, payload: ProjectUpdate):
    project = get_project(db, project_id)
    if not project:
        return None

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int):
    project = get_project(db, project_id)
    if not project:
        return False

    db.delete(project)
    db.commit()
    return True
