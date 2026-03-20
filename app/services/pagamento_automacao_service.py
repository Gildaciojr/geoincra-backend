from sqlalchemy.orm import Session
from datetime import datetime

from app.models.pagamento import Pagamento
from app.models.project_status import ProjectStatus
from app.models.documento_tecnico import DocumentoTecnico


class PagamentoAutomacaoService:

    @staticmethod
    def avaliar_liberacao_pagamento(
        db: Session,
        pagamento: Pagamento,
    ) -> Pagamento:

        try:
            parcelas = pagamento.parcelas
            if not parcelas:
                return pagamento

            status_atual = (
                db.query(ProjectStatus)
                .filter(
                    ProjectStatus.project_id == pagamento.project_id,
                    ProjectStatus.ativo.is_(True),
                )
                .first()
            )

            docs_aprovados = (
                db.query(DocumentoTecnico)
                .join(DocumentoTecnico.imovel)
                .filter(DocumentoTecnico.imovel.has(project_id=pagamento.project_id))
                .filter(DocumentoTecnico.status_tecnico == "APROVADO")
                .filter(DocumentoTecnico.is_versao_atual.is_(True))
                .count()
            )

            for parcela in parcelas:
                if parcela.liberada:
                    continue

                if parcela.ordem == 1 and status_atual:
                    parcela.liberada = True
                    parcela.liberada_em = datetime.utcnow()

                elif parcela.ordem == 2 and docs_aprovados > 0:
                    parcela.liberada = True
                    parcela.liberada_em = datetime.utcnow()

                elif (
                    parcela.ordem == 3
                    and status_atual
                    and status_atual.status == "FINALIZADO"
                ):
                    parcela.liberada = True
                    parcela.liberada_em = datetime.utcnow()

            # 🔥 NÃO COMMITA AQUI
            return pagamento

        except Exception as e:
            print(f"⚠️ Falha na automação de pagamento: {str(e)}")
            return pagamento