# app/seed/seed_calculation_parameters_extra.py

from app.core.database import SessionLocal
from app.models.calculation_parameter import CalculationParameter

PARAMS = [

    # ---------------------------------------------------------
    #   FAIXAS DE HECTARES
    # ---------------------------------------------------------
    {"nome": "faixa_4_8_valor_por_ha", "valor": 750.00, "unidade": "ha", "categoria": "base"},
    {"nome": "faixa_4_8_minimo", "valor": 3000.00, "unidade": "R$", "categoria": "base"},

    {"nome": "faixa_8_16_valor_por_ha", "valor": 500.00, "unidade": "ha", "categoria": "base"},
    {"nome": "faixa_8_16_minimo", "valor": 4000.00, "unidade": "R$", "categoria": "base"},

    {"nome": "faixa_16_25_valor_por_ha", "valor": 400.00, "unidade": "ha", "categoria": "base"},
    {"nome": "faixa_16_25_minimo", "valor": 6400.00, "unidade": "R$", "categoria": "base"},

    {"nome": "faixa_25_50_valor_por_ha", "valor": 300.00, "unidade": "ha", "categoria": "base"},
    {"nome": "faixa_25_50_minimo", "valor": 7500.00, "unidade": "R$", "categoria": "base"},

    {"nome": "faixa_50_100_valor_por_ha", "valor": 200.00, "unidade": "ha", "categoria": "base"},
    {"nome": "faixa_50_100_minimo", "valor": 10000.00, "unidade": "R$", "categoria": "base"},

    # ---------------------------------------------------------
    #   VARIÁVEIS ADICIONAIS
    # ---------------------------------------------------------
    {"nome": "confrontacao_rios", "valor": 50.0, "unidade": "%", "categoria": "variavel"},
    {"nome": "proprietario_acompanha", "valor": -10.0, "unidade": "%", "categoria": "variavel"},
    {"nome": "mata_mais_50", "valor": 60.0, "unidade": "%", "categoria": "variavel"},

    # Finalidades
    {"nome": "unificacao", "valor": 15.0, "unidade": "%", "categoria": "finalidade"},
    {"nome": "desmembramento_ate_3", "valor": 200.0, "unidade": "%", "categoria": "finalidade"},
    {"nome": "desmembramento_5", "valor": 400.0, "unidade": "%", "categoria": "finalidade"},
    {"nome": "desmembramento_6", "valor": 500.0, "unidade": "%", "categoria": "finalidade"},
    {"nome": "desmembramento_7", "valor": 600.0, "unidade": "%", "categoria": "finalidade"},
    {"nome": "desmembramento_extra", "valor": 100.0, "unidade": "%", "categoria": "finalidade"},

    # ---------------------------------------------------------
    #   DOCUMENTOS
    # ---------------------------------------------------------
    {"nome": "ccir_nao_atualizado", "valor": 100.0, "unidade": "R$", "categoria": "documento"},
    {"nome": "itr_nao_atualizado", "valor": 50.0, "unidade": "R$", "categoria": "documento"},
    {"nome": "certificado_digital_nao_possui", "valor": 70.0, "unidade": "R$", "categoria": "documento"},

    # ---------------------------------------------------------
    #   SERVIÇOS ADICIONAIS
    # ---------------------------------------------------------
    {"nome": "estaqueamento_km", "valor": 1600.0, "unidade": "R$/km", "categoria": "servico"},
    {"nome": "notificacao_confrontante", "valor": 180.0, "unidade": "R$", "categoria": "servico"},

    # ---------------------------------------------------------
    #   ART
    # ---------------------------------------------------------
    {"nome": "valor_art", "valor": 200.0, "unidade": "R$", "categoria": "art"},

    # ART - quantidade
    {"nome": "qtd_art_padrao", "valor": 1, "unidade": "un", "categoria": "art"},
    {"nome": "qtd_art_desmembramento", "valor": 2, "unidade": "un", "categoria": "art"},
    {"nome": "qtd_art_terra_legal", "valor": 2, "unidade": "un", "categoria": "art"},


    # ---------------------------------------------------------
    #   DESPESAS CARTORÁRIAS
    # ---------------------------------------------------------
    {"nome": "cartorio_escritura_ate_28493", "valor": 407.35, "unidade": "R$", "categoria": "cartorio"},
    {"nome": "cartorio_registro_ate_28493", "valor": 234.40, "unidade": "R$", "categoria": "cartorio"},
    {"nome": "certidao_onus_reais", "valor": 20.0, "unidade": "R$", "categoria": "cartorio"},

    # ITBI
    {"nome": "itbi_percentual", "valor": 2.0, "unidade": "%", "categoria": "cartorio"},
]


def seed_extra():
    db = SessionLocal()
    try:
        for p in PARAMS:
            exists = (
                db.query(CalculationParameter)
                .filter(CalculationParameter.nome == p["nome"])
                .first()
            )
            if exists:
                continue

            param = CalculationParameter(
                nome=p["nome"],
                descricao=p["nome"].replace("_", " ").title(),
                valor=p["valor"],
                unidade=p["unidade"],
                categoria=p["categoria"],
            )

            db.add(param)

        db.commit()
        print("✅ Seeder EXTRA concluído! Parâmetros adicionais inseridos!")

    except Exception as e:
        print("❌ ERRO NO SEEDER EXTRA:", e)

    finally:
        db.close()


if __name__ == "__main__":
    seed_extra()
