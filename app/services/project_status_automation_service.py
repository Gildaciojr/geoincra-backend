from sqlalchemy.orm import Session

from app.models.project_status import ProjectStatus
from app.models.documento_tecnico import DocumentoTecnico
from app.models.geometria import Geometria
from app.crud.project_status_crud import definir_status_projeto
from app.schemas.project_status import ProjectStatusCreate


class ProjectStatusAutomationService:
    """
    Motor de decisão automática do status do projeto.
    """

    @staticmethod
    def avaliar_e_atualizar_status(db: Session, project_id: int):
        """
        Avalia o estado atual do projeto e define o status correto.
        """

        # =====================================================
        # 1️⃣ Buscar documentos técnicos ATUAIS
        # =====================================================
        docs = (
            db.query(DocumentoTecnico)
            .join(DocumentoTecnico.imovel)
            .filter(DocumentoTecnico.is_versao_atual.is_(True))
            .filter(DocumentoTecnico.imovel.has(project_id=project_id))
            .all()
        )

        if not docs:
            ProjectStatusAutomationService._definir(
                db,
                project_id,
                status="CADASTRADO",
                descricao="Projeto criado, sem documentos técnicos.",
            )
            return

        # =====================================================
        # 2️⃣ Se algum documento exigir correção
        # =====================================================
        if any(doc.status_tecnico == "CORRIGIR" for doc in docs):
            ProjectStatusAutomationService._definir(
                db,
                project_id,
                status="AJUSTES_SOLICITADOS",
                descricao="Há documentos técnicos pendentes de correção.",
            )
            return

        # =====================================================
        # 3️⃣ Se ainda houver documentos em análise
        # =====================================================
        if any(doc.status_tecnico in ("RASCUNHO", "EM_ANALISE") for doc in docs):
            ProjectStatusAutomationService._definir(
                db,
                project_id,
                status="DOCUMENTOS_EM_ANALISE",
                descricao="Documentos técnicos em análise.",
            )
            return

        # =====================================================
        # 4️⃣ Todos os documentos técnicos aprovados
        # =====================================================
        if all(doc.status_tecnico == "APROVADO" for doc in docs):
            ProjectStatusAutomationService._definir(
                db,
                project_id,
                status="APROVADO_TECNICAMENTE",
                descricao="Todos os documentos técnicos foram aprovados.",
            )

        # =====================================================
        # 5️⃣ Verificar prontidão SIGEF
        # =====================================================
        geometrias = (
            db.query(Geometria)
            .join(Geometria.imovel)
            .filter(Geometria.imovel.has(project_id=project_id))
            .all()
        )

        geometrias_validas = [
            g for g in geometrias
            if g.geojson and g.area_hectares and g.perimetro_m
        ]

        tipos_docs = {doc.document_group_key for doc in docs}

        obrigatorios = {"MEMORIAL", "CROQUI"}

        if geometrias_validas and obrigatorios.issubset(tipos_docs):
            ProjectStatusAutomationService._definir(
                db,
                project_id,
                status="PRONTO_PARA_SIGEF",
                descricao="Projeto tecnicamente completo e pronto para envio ao SIGEF.",
            )

    # =====================================================
    # MÉTODO INTERNO
    # =====================================================
    @staticmethod
    def _definir(
        db: Session,
        project_id: int,
        status: str,
        descricao: str,
    ):
        definir_status_projeto(
            db,
            project_id,
            ProjectStatusCreate(
                status=status,
                descricao=descricao,
                definido_automaticamente=True,
            ),
        )
