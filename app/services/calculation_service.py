# geoincra_backend/app/services/calculation_service.py
from sqlalchemy.orm import Session
from app.models.calculation_parameter import CalculationParameter
from app.schemas.calculation import CalculationBase, CalculationResult


class CalculationService:

    @staticmethod
    def param(db: Session, name: str) -> float:
        param = (
            db.query(CalculationParameter)
            .filter(CalculationParameter.nome == name)
            .first()
        )
        return float(param.valor) if param else 0.0

    @staticmethod
    def calcular_valor_base(db: Session, area: float) -> float:
        if area < 4:
            raise ValueError("Área mínima para cálculo é 4 hectares.")

        faixas = [
            (4, 8, "faixa_4_8"),
            (8, 16, "faixa_8_16"),
            (16, 25, "faixa_16_25"),
            (25, 50, "faixa_25_50"),
            (50, 100, "faixa_50_100"),
        ]

        for min_a, max_a, key in faixas:
            if min_a <= area < max_a:
                valor_ha = CalculationService.param(db, f"{key}_valor_por_ha")
                minimo = CalculationService.param(db, f"{key}_minimo")
                return max(valor_ha * area, minimo)

        raise ValueError("Área fora das faixas configuradas.")

    @staticmethod
    def calcular_finalidade(db: Session, finalidade: str, partes: int | None) -> float:
        if finalidade == "unificacao":
            return CalculationService.param(db, "unificacao")

        if finalidade == "averbacao":
            return 0.0

        if finalidade == "desmembramento":
            if not partes or partes < 2:
                raise ValueError("Desmembramento exige número de partes >= 2.")

            if partes <= 3:
                return CalculationService.param(db, "desmembramento_ate_3")
            if partes == 5:
                return CalculationService.param(db, "desmembramento_5")
            if partes == 6:
                return CalculationService.param(db, "desmembramento_6")
            if partes == 7:
                return CalculationService.param(db, "desmembramento_7")

            extra = CalculationService.param(db, "desmembramento_extra")
            return (
                CalculationService.param(db, "desmembramento_7")
                + (partes - 7) * extra
            )

        # terra_legal etc. pode virar parâmetro futuramente
        return 0.0

    # ---------------------------
    # ART: quantidade e total
    # ---------------------------
    @staticmethod
    def calcular_art(db: Session, finalidade: str) -> tuple[int, float]:
        """
        Regras mínimas coerentes com escopo:
        - padrão: 1 ART
        - desmembramento: normalmente 2 (pode ajustar via parâmetro depois)
        - terra_legal: normalmente 2 (ajustável)
        """
        valor_unit = CalculationService.param(db, "valor_art")

        if finalidade in ("desmembramento", "terra_legal"):
            qtd = int(CalculationService.param(db, "qtd_art_desmembramento") or 2) if finalidade == "desmembramento" else int(CalculationService.param(db, "qtd_art_terra_legal") or 2)
        else:
            qtd = int(CalculationService.param(db, "qtd_art_padrao") or 1)

        return qtd, float(valor_unit) * qtd

    # ---------------------------
    # Cartório / ITBI (com breakdown)
    # ---------------------------
    @staticmethod
    def calcular_cartorio(db: Session, vti: float | None) -> dict:
        """
        MVP fiel ao documento do cliente via parâmetros:
        - escritura/registo/certidão por faixa (começando pela faixa até 28.493)
        - itbi em % sobre vti
        """
        if not vti or vti <= 0:
            return {
                "escritura": 0.0,
                "registro": 0.0,
                "certidao_onus_reais": 0.0,
                "itbi": 0.0,
                "total": 0.0,
                "itbi_percentual": float(CalculationService.param(db, "itbi_percentual") or 0.0),
            }

        # (Você pode evoluir p/ múltiplas faixas depois, sem quebrar contrato)
        escritura = CalculationService.param(db, "cartorio_escritura_ate_28493")
        registro = CalculationService.param(db, "cartorio_registro_ate_28493")
        certidao = CalculationService.param(db, "certidao_onus_reais")
        itbi_pct = CalculationService.param(db, "itbi_percentual")

        itbi = (float(vti) * float(itbi_pct)) / 100.0 if itbi_pct else 0.0
        total = float(escritura) + float(registro) + float(certidao) + float(itbi)

        return {
            "escritura": float(escritura),
            "registro": float(registro),
            "certidao_onus_reais": float(certidao),
            "itbi": float(itbi),
            "total": float(total),
            "itbi_percentual": float(itbi_pct),
        }

    @staticmethod
    def calcular(db: Session, req: CalculationBase) -> CalculationResult:
        base = CalculationService.calcular_valor_base(db, req.area_hectares)

        percentuais = 0.0
        if req.confrontacao_rios:
            percentuais += CalculationService.param(db, "confrontacao_rios")
        if req.proprietario_acompanha:
            percentuais += CalculationService.param(db, "proprietario_acompanha")
        if req.mata_mais_50:
            percentuais += CalculationService.param(db, "mata_mais_50")

        percentuais += CalculationService.calcular_finalidade(db, req.finalidade, req.partes)
        valor_pct = base * (percentuais / 100)

        fixos = 0.0
        if not req.ccir_atualizado:
            fixos += CalculationService.param(db, "ccir_nao_atualizado")
        if not req.itr_atualizado:
            fixos += CalculationService.param(db, "itr_nao_atualizado")
        if not req.certificado_digital:
            fixos += CalculationService.param(db, "certificado_digital_nao_possui")

        fixos += req.estaqueamento_km * CalculationService.param(db, "estaqueamento_km")
        fixos += req.notificacao_confrontantes * CalculationService.param(db, "notificacao_confrontante")

        qtd_arts, valor_art_total = CalculationService.calcular_art(db, req.finalidade)
        cart = CalculationService.calcular_cartorio(db, req.vti_imovel)

        total = base + valor_pct + fixos + valor_art_total + cart["total"]

        # mantém o schema atual (sem quebrar), mas você vai repassar breakdown via proposal_service
        return CalculationResult(
            valor_base=base,
            valor_variaveis_percentuais=valor_pct,
            valor_variaveis_fixas=fixos,
            valor_art=valor_art_total,
            valor_cartorio=cart["total"],
            total_final=total,
        )
