from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.pagamento import Pagamento
from app.models.parcela_pagamento import ParcelaPagamento
from app.models.pagamento_evento import PagamentoEvento

# NOVOS IMPORTS (workflow automático)
from app.services.pagamento_automacao_service import PagamentoAutomacaoService
from app.services.project_automacao_service import ProjectAutomacaoService


class PagamentoService:
    MODELOS_PADRAO = {
        "20_30_50": [
            ("ENTRADA", 20.0),
            ("MEIO", 30.0),
            ("FINAL", 50.0),
        ],
        "50_50": [
            ("ENTRADA", 50.0),
            ("FINAL", 50.0),
        ],
        "100": [
            ("UNICA", 100.0),
        ],
    }

    STATUS_PENDENTE = "PENDENTE"
    STATUS_PARCIAL = "PARCIAL"
    STATUS_PAGO = "PAGO"
    STATUS_ATRASADO = "ATRASADO"
    STATUS_CANCELADO = "CANCELADO"

    PARCELA_PENDENTE = "PENDENTE"
    PARCELA_PAGA = "PAGO"
    PARCELA_ATRASADA = "ATRASADA"
    PARCELA_CANCELADA = "CANCELADA"

    @staticmethod
    def registrar_evento(db: Session, pagamento_id: int, tipo: str, descricao=None, metadata_json=None, criado_por_usuario_id=None):
        ev = PagamentoEvento(
            pagamento_id=pagamento_id,
            tipo=tipo,
            descricao=descricao,
            metadata_json=metadata_json,
            criado_por_usuario_id=criado_por_usuario_id,
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev

    @staticmethod
    def _gerar_vencimento_padrao(indice: int) -> datetime:
        base = datetime.utcnow()
        if indice == 0:
            return base + timedelta(days=2)
        if indice == 1:
            return base + timedelta(days=15)
        return base + timedelta(days=30)

    @staticmethod
    def gerar_parcelas_padrao(db: Session, pagamento: Pagamento):
        if pagamento.status == PagamentoService.STATUS_CANCELADO:
            raise ValueError("Pagamento cancelado não pode gerar parcelas.")

        modelo = pagamento.modelo
        if modelo not in PagamentoService.MODELOS_PADRAO and modelo != "CUSTOM":
            raise ValueError("Modelo de pagamento inválido.")

        existentes = (
            db.query(ParcelaPagamento)
            .filter(ParcelaPagamento.pagamento_id == pagamento.id)
            .order_by(ParcelaPagamento.ordem.asc())
            .all()
        )
        if existentes:
            return existentes

        if modelo == "CUSTOM":
            raise ValueError("Modelo CUSTOM exige criação manual de parcelas.")

        definicao = PagamentoService.MODELOS_PADRAO[modelo]

        parcelas = []
        for idx, (ref, pct) in enumerate(definicao, start=1):
            valor = round((pagamento.total * pct) / 100.0, 2)

            parcela = ParcelaPagamento(
                pagamento_id=pagamento.id,
                ordem=idx,
                percentual=pct,
                valor=valor,
                vencimento=PagamentoService._gerar_vencimento_padrao(idx - 1),
                status=PagamentoService.PARCELA_PENDENTE,
                referencia_interna=ref,
                liberada=False,
            )

            db.add(parcela)
            parcelas.append(parcela)

        db.commit()
        for p in parcelas:
            db.refresh(p)

        PagamentoService.registrar_evento(
            db=db,
            pagamento_id=pagamento.id,
            tipo="PARCELAS_GERADAS",
            descricao=f"Parcelas geradas automaticamente pelo modelo {modelo}.",
            metadata_json={"modelo": modelo, "qtd": len(parcelas)},
        )

        PagamentoService.recalcular_status_pagamento(db, pagamento.id)

        # NOVO — atualizar automação de liberação financeira
        PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)

        return parcelas


    @staticmethod
    def recalcular_status_pagamento(db: Session, pagamento_id: int) -> Pagamento:
        pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
        if not pagamento:
            raise ValueError("Pagamento não encontrado.")

        if pagamento.status == PagamentoService.STATUS_CANCELADO:
            return pagamento

        parcelas = db.query(ParcelaPagamento).filter(ParcelaPagamento.pagamento_id == pagamento_id).all()

        if not parcelas:
            pagamento.status = PagamentoService.STATUS_PENDENTE
            db.commit()
            db.refresh(pagamento)
            return pagamento

        total_pago = sum(p.valor for p in parcelas if p.status == PagamentoService.PARCELA_PAGA)
        total_geral = sum(p.valor for p in parcelas if p.status != PagamentoService.PARCELA_CANCELADA)

        now = datetime.utcnow()

        for p in parcelas:
            if p.status == PagamentoService.PARCELA_PENDENTE and p.vencimento and p.vencimento < now:
                p.status = PagamentoService.PARCELA_ATRASADA
                p.updated_at = now

        parcelas_atrasadas = any(p.status == PagamentoService.PARCELA_ATRASADA for p in parcelas)

        if total_geral <= 0:
            pagamento.status = PagamentoService.STATUS_PENDENTE
        elif total_pago <= 0:
            pagamento.status = PagamentoService.STATUS_ATRASADO if parcelas_atrasadas else PagamentoService.STATUS_PENDENTE
        elif total_pago < total_geral:
            pagamento.status = PagamentoService.STATUS_ATRASADO if parcelas_atrasadas else PagamentoService.STATUS_PARCIAL
        else:
            pagamento.status = PagamentoService.STATUS_PAGO

        pagamento.updated_at = now
        db.commit()
        db.refresh(pagamento)

        # NOVO — recalcular status global do projeto automaticamente
        ProjectAutomacaoService.aplicar_status_automatico(db, pagamento.project_id)

        return pagamento

    @staticmethod
    def marcar_parcela_paga(
        db: Session,
        parcela_id: int,
        forma_pagamento: str | None = None,
        observacoes: str | None = None,
        pago_em: datetime | None = None,
    ) -> ParcelaPagamento:
        parcela = db.query(ParcelaPagamento).filter(ParcelaPagamento.id == parcela_id).first()
        if not parcela:
            raise ValueError("Parcela não encontrada.")

        pagamento = db.query(Pagamento).filter(Pagamento.id == parcela.pagamento_id).first()
        if not pagamento:
            raise ValueError("Pagamento não encontrado.")
        if pagamento.status == PagamentoService.STATUS_CANCELADO:
            raise ValueError("Pagamento cancelado não permite baixa de parcela.")

        parcela.status = PagamentoService.PARCELA_PAGA
        parcela.pago_em = pago_em or datetime.utcnow()
        parcela.forma_pagamento = forma_pagamento
        parcela.observacoes = observacoes
        parcela.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(parcela)

        PagamentoService.registrar_evento(
            db=db,
            pagamento_id=pagamento.id,
            tipo="PARCELA_PAGA",
            descricao=f"Parcela {parcela.ordem} marcada como paga.",
            metadata_json={
                "parcela_id": parcela.id,
                "numero": parcela.ordem,
                "valor": parcela.valor,
                "forma": forma_pagamento,
            },
        )

        PagamentoService.recalcular_status_pagamento(db, pagamento.id)

        # NOVO — automação financeira e técnica
        PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)
        ProjectAutomacaoService.aplicar_status_automatico(db, pagamento.project_id)

        return parcela

    @staticmethod
    def obter_percentual_pago(db: Session, pagamento_id: int) -> float:
        parcelas = db.query(ParcelaPagamento).filter(ParcelaPagamento.pagamento_id == pagamento_id).all()
        if not parcelas:
            return 0.0

        total_pago = sum(p.valor for p in parcelas if p.status == PagamentoService.PARCELA_PAGA)
        total_geral = sum(p.valor for p in parcelas if p.status != PagamentoService.PARCELA_CANCELADA)

        if total_geral <= 0:
            return 0.0

        return round((total_pago / total_geral) * 100.0, 2)

    @staticmethod
    def liberar_condicional(db: Session, pagamento_id: int) -> dict:
        pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
        if not pagamento:
            raise ValueError("Pagamento não encontrado.")

        pct = PagamentoService.obter_percentual_pago(db, pagamento_id)

        return {
            "pagamento_id": pagamento_id,
            "status": pagamento.status,
            "percentual_pago": pct,
            "liberar_iniciar": pct >= 20.0,
            "liberar_meio": pct >= 50.0,
            "liberar_final": pct >= 100.0,
        }
