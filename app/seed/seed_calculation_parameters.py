# app/seed/seed_calculation_parameters.py

from app.core.database import SessionLocal
from app.models.calculation_parameter import CalculationParameter


"""
Seeder compatível com o modelo atual:
Campos existentes na tabela:
- nome
- descricao
- valor
- unidade
- categoria
"""

PARAMETERS = [
    # ---------------------------
    # TABELA DE HECTARES 
    # ---------------------------
    {
        "nome": "ha_4_8_preco_por_hectare",
        "descricao": "Valor por hectare para imóveis entre 4 e 8 ha",
        "valor": 750.0,
        "unidade": "BRL_POR_HA",
        "categoria": "hectares",
    },
    {
        "nome": "ha_4_8_valor_minimo",
        "descricao": "Valor mínimo total para imóveis entre 4 e 8 ha",
        "valor": 3000.0,
        "unidade": "BRL",
        "categoria": "hectares",
    },

    {
        "nome": "ha_8_16_preco_por_hectare",
        "descricao": "Valor por hectare para imóveis entre 8 e 16 ha",
        "valor": 500.0,
        "unidade": "BRL_POR_HA",
        "categoria": "hectares",
    },
    {
        "nome": "ha_8_16_valor_minimo",
        "descricao": "Valor mínimo total para imóveis entre 8 e 16 ha",
        "valor": 4000.0,
        "unidade": "BRL",
        "categoria": "hectares",
    },

    {
        "nome": "ha_16_25_preco_por_hectare",
        "descricao": "Valor por hectare para imóveis entre 16 e 25 ha",
        "valor": 400.0,
        "unidade": "BRL_POR_HA",
        "categoria": "hectares",
    },
    {
        "nome": "ha_16_25_valor_minimo",
        "descricao": "Valor mínimo total para imóveis entre 16 e 25 ha",
        "valor": 3800.0,
        "unidade": "BRL",
        "categoria": "hectares",
    },

    {
        "nome": "ha_25_50_preco_por_hectare",
        "descricao": "Valor por hectare para imóveis entre 25 e 50 ha",
        "valor": 300.0,
        "unidade": "BRL_POR_HA",
        "categoria": "hectares",
    },
    {
        "nome": "ha_25_50_valor_minimo",
        "descricao": "Valor mínimo total para imóveis entre 25 e 50 ha",
        "valor": 4000.0,
        "unidade": "BRL",
        "categoria": "hectares",
    },

    {
        "nome": "ha_50_100_preco_por_hectare",
        "descricao": "Valor por hectare para imóveis entre 50 e 100 ha",
        "valor": 200.0,
        "unidade": "BRL_POR_HA",
        "categoria": "hectares",
    },
    {
        "nome": "ha_50_100_valor_minimo",
        "descricao": "Valor mínimo total para imóveis entre 50 e 100 ha",
        "valor": 4500.0,
        "unidade": "BRL",
        "categoria": "hectares",
    },

    # ---------------------------
    # VARIÁVEIS (%)
    # ---------------------------
    {
        "nome": "confrontacao_rios_acrescimo",
        "descricao": "Acréscimo se confronta com rios",
        "valor": 50.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "variaveis",
    },
    {
        "nome": "proprietario_acompanha_desconto",
        "descricao": "Desconto se o proprietário acompanha",
        "valor": 10.0,
        "unidade": "PERCENT_MINUS",
        "categoria": "variaveis",
    },
    {
        "nome": "mais50_mata_acrescimo",
        "descricao": "Acréscimo se mais de 50% é mata",
        "valor": 60.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "variaveis",
    },

    # ---------------------------
    # FINALIDADES
    # ---------------------------
    {
        "nome": "desmembramento_ate_3_partes",
        "descricao": "Acréscimo para desmembramento até 3 partes",
        "valor": 200.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "finalidade",
    },
    {
        "nome": "desmembramento_5_partes",
        "descricao": "Acréscimo para desmembramento em 5 partes",
        "valor": 400.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "finalidade",
    },
    {
        "nome": "desmembramento_6_partes",
        "descricao": "Acréscimo para desmembramento em 6 partes",
        "valor": 500.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "finalidade",
    },
    {
        "nome": "desmembramento_7_partes",
        "descricao": "Acréscimo para desmembramento em 7 partes",
        "valor": 600.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "finalidade",
    },
    {
        "nome": "desmembramento_extra_por_parte",
        "descricao": "Acréscimo adicional por parte acima de 7",
        "valor": 100.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "finalidade",
    },
    {
        "nome": "unificacao_acrescimo",
        "descricao": "Acréscimo para unificação",
        "valor": 15.0,
        "unidade": "PERCENT_PLUS",
        "categoria": "finalidade",
    },

    # ---------------------------
    # DOCUMENTOS
    # ---------------------------
    {
        "nome": "ccir_nao_atualizado",
        "descricao": "Taxa se CCIR não está atualizado",
        "valor": 100.0,
        "unidade": "BRL",
        "categoria": "documentos",
    },
    {
        "nome": "itr_nao_atualizado",
        "descricao": "Taxa se ITR não está atualizado",
        "valor": 50.0,
        "unidade": "BRL",
        "categoria": "documentos",
    },
    {
        "nome": "certificado_digital_ausente",
        "descricao": "Taxa por proprietário sem certificado digital",
        "valor": 70.0,
        "unidade": "BRL",
        "categoria": "documentos",
    },

    # ---------------------------
    # SERVIÇOS EXTRAS
    # ---------------------------
    {
        "nome": "estaqueamento_por_km",
        "descricao": "Valor por km de estaqueamento",
        "valor": 1600.0,
        "unidade": "BRL_POR_KM",
        "categoria": "extras",
    },

    # ---------------------------
    # PAGAMENTOS
    # ---------------------------
    {
        "nome": "pagamento_validacao_docs",
        "descricao": "Percentual liberado após validação",
        "valor": 20.0,
        "unidade": "PERCENT",
        "categoria": "pagamento",
    },
    {
        "nome": "pagamento_visita_tecnica",
        "descricao": "Percentual liberado após visita técnica",
        "valor": 30.0,
        "unidade": "PERCENT",
        "categoria": "pagamento",
    },
    {
        "nome": "pagamento_entrega_final",
        "descricao": "Percentual liberado após entrega",
        "valor": 50.0,
        "unidade": "PERCENT",
        "categoria": "pagamento",
    },
]


def seed_calculation_parameters():
    db = SessionLocal()

    try:
        count = db.query(CalculationParameter).count()
        if count > 0:
            print(f"⚠️ Já existem {count} parâmetros. Seed ignorado.")
            return

        for item in PARAMETERS:
            db.add(CalculationParameter(**item))

        db.commit()

        print(f"✅ Seeder concluído! {len(PARAMETERS)} parâmetros inseridos!")

    except Exception as e:
        print("❌ Erro ao executar o seeder de parâmetros de cálculo:", e)

    finally:
        db.close()


if __name__ == "__main__":
    seed_calculation_parameters()
