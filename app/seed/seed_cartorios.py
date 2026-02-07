# app/seed/seed_cartorios.py

from app.core.database import SessionLocal
from app.models.cartorio import Cartorio


# -------------------------------------------------------------------
# LISTA COMPLETA DE CARTÓRIOS DE RONDÔNIA
# -------------------------------------------------------------------
CARTORIOS_DATA = [
    {
        "nome": "1º Ofício de Registro de Imóveis, Títulos e Documentos e Civis das Pessoas Jurídicas",
        "municipio": "Cacoal",
        "estado": "RO",
        "telefone": "(69) 3441-4463",
        "email": "primeirori@registrocacoal.com.br",
        "endereco": "Rua dos Pioneiros, 1.876 - Centro - Cacoal - RO",
        "tipo": "Registro de Imóveis",
    },
    {
        "nome": "2º Ofício de Registro de Imóveis",
        "municipio": "Cacoal",
        "estado": "RO",
        "telefone": "(69) 3443-3662",
        "email": "segundoricacoal@gmail.com",
        "endereco": "Av. Sete de Setembro, 2772 - Princesa Isabel - Cacoal - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- PORTO VELHO -----------------------------
    {
        "nome": "1º Ofício de Registro de Imóveis",
        "municipio": "Porto Velho",
        "estado": "RO",
        "telefone": "(69) 99242-3444",
        "email": "contato@1ripvh.com",
        "endereco": "Rua Equador, 1870 - Nova Porto Velho - Porto Velho - RO",
        "tipo": "Registro de Imóveis",
    },
    {
        "nome": "2º Ofício de Registro de Imóveis",
        "municipio": "Porto Velho",
        "estado": "RO",
        "telefone": "(69) 3302-0602",
        "email": "contato@segundoriportovelho.com",
        "endereco": "Avenida Carlos Gomes, 2581 - São Cristóvão - Porto Velho - RO",
        "tipo": "Registro de Imóveis",
    },
    {
        "nome": "3º Ofício de Registro de Imóveis",
        "municipio": "Porto Velho",
        "estado": "RO",
        "telefone": "(69) 3224-2864",
        "email": "3imoveis_pvh@tjro.jus.br",
        "endereco": "Rua Afonso Pena, 161 - Centro - Porto Velho - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- GUAJARÁ-MIRIM -----------------------------
    {
        "nome": "Cartório de Registro Civil e Imóveis, RTD e RCPJ",
        "municipio": "Guajará-Mirim",
        "estado": "RO",
        "telefone": "(69) 3541-1880",
        "email": "civileimoveis_guajara@tjro.jus.br",
        "endereco": "Avenida Marechal Deodoro, 1096 - Centro - Guajará-Mirim - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- VILHENA -----------------------------
    {
        "nome": "1º Registro de Imóveis, Títulos e Documentos e Pessoas Jurídicas",
        "municipio": "Vilhena",
        "estado": "RO",
        "telefone": "(69) 3321-2706",
        "email": None,
        "endereco": "Rua Juscelino Kubitschek, 411 - Centro - Vilhena - RO",
        "tipo": "Registro de Imóveis",
    },
    {
        "nome": "2º Ofício de Registro de Imóveis",
        "municipio": "Vilhena",
        "estado": "RO",
        "telefone": "(69) 3322-0004",
        "email": "contato@cartoriomarechalrondon.com.br",
        "endereco": "Rua Afonso Pena, 145 - Centro - Vilhena - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- JI-PARANÁ -----------------------------
    {
        "nome": "1º Ofício de Registro de Imóveis, Títulos e Documentos e Civil das Pessoas Jurídicas",
        "municipio": "Ji-Paraná",
        "estado": "RO",
        "telefone": "(69) 3421-3065",
        "email": "cartoriojp.imoveis@gmail.com",
        "endereco": "Rua Julio Guerra, 655 - Centro - Ji-Paraná - RO",
        "tipo": "Registro de Imóveis",
    },
    {
        "nome": "2º Ofício de Registro de Imóveis",
        "municipio": "Ji-Paraná",
        "estado": "RO",
        "telefone": "(69) 3422-8573",
        "email": "2imoveis_ji-parana@tjro.jus.br",
        "endereco": "Av. Tabapuã, 2447 - Sala 05 - Centro - Ji-Paraná - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- PIMENTA BUENO -----------------------------
    {
        "nome": "Cartório de Registro de Imóveis e Anexos",
        "municipio": "Pimenta Bueno",
        "estado": "RO",
        "telefone": "(69) 3451-2064",
        "email": "cartorioimoveispb@hotmail.com",
        "endereco": "Avenida Presidente Kennedy, 1127 - Centro - Pimenta Bueno - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- ESPIGÃO D'OESTE -----------------------------
    {
        "nome": "Ofício de Registro de Imóveis, Títulos e Documentos e Civil das Pessoas Jurídicas e Tabelionato de Protesto de Títulos",
        "municipio": "Espigão d'Oeste",
        "estado": "RO",
        "telefone": "(69) 3481-2650",
        "email": None,
        "endereco": "Rua Independência, 2169 - Centro - Espigão d'Oeste - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- JARU -----------------------------
    {
        "nome": "Cartório de Registro de Imóveis, Títulos e Documentos e Pessoas Jurídicas",
        "municipio": "Jaru",
        "estado": "RO",
        "telefone": "(69) 3521-1211",
        "email": "regimoveisjaru@speedweb.com.br",
        "endereco": "Av. Rio Branco, 2010 - Setor 02 - Jaru - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- ARIQUEMES -----------------------------
    {
        "nome": "Ofício de Registro de Imóveis, Títulos e Documentos e Pessoas Jurídicas",
        "municipio": "Ariquemes",
        "estado": "RO",
        "telefone": "(69) 3535-2651",
        "email": "criariquemes@hotmail.com",
        "endereco": "Rua Vitória Régia, 2160 - Setor 04 - Ariquemes - RO",
        "tipo": "Registro de Imóveis",
    },
    {
        "nome": "2º Ofício de Registro de Imóveis",
        "municipio": "Ariquemes",
        "estado": "RO",
        "telefone": "(69) 3536-5694",
        "email": "2imoveis_ariquemes@tjro.jus.br",
        "endereco": "Av. Tabapuã, 2447 - Sala 05 - Centro - Ariquemes - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- ROLIM DE MOURA -----------------------------
    {
        "nome": "Serviço Registral de Imóveis, Títulos e Documentos e Civil de Pessoas Jurídicas",
        "municipio": "Rolim de Moura",
        "estado": "RO",
        "telefone": "(69) 3442-1930",
        "email": "imoveis_rolimdemoura@tjro.jus.br",
        "endereco": "Avenida Rio Branco, 4449 - Centro - Rolim de Moura - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- ALVORADA D'OESTE -----------------------------
    {
        "nome": "Tabelionato de Protestos, Registro de Imóveis, RTD e RCPJ",
        "municipio": "Alvorada d'Oeste",
        "estado": "RO",
        "telefone": "(69) 3412-2122",
        "email": "milton33@superig.com.br",
        "endereco": "Rua Guimarães Rosa, 4896 - Centro - Alvorada d'Oeste - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- COSTA MARQUES -----------------------------
    {
        "nome": "Ofício Único",
        "municipio": "Costa Marques",
        "estado": "RO",
        "telefone": "(69) 3651-3712",
        "email": "cartoriocmarques@gmail.com",
        "endereco": "Avenida Chianca, 1900 - Centro - Costa Marques - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- SÃO FRANCISCO DO GUAPORÉ -----------------------------
    {
        "nome": "Ofício de Registro de Imóveis, Títulos e Documentos e Civis das Pessoas Jurídicas",
        "municipio": "São Francisco do Guaporé",
        "estado": "RO",
        "telefone": "(69) 3621-2537",
        "email": "cartoriosjsafira@hotmail.com",
        "endereco": "Rua Sete de Setembro, 4178 - Centro - São Francisco do Guaporé - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- COLORADO DO OESTE -----------------------------
    {
        "nome": "Tabelionato de Protesto, Registro de Imóveis, RTD e RCPJ",
        "municipio": "Colorado do Oeste",
        "estado": "RO",
        "telefone": "(69) 3341-1177",
        "email": "imoveisprot_colorado@hotmail.com",
        "endereco": "Avenida Rio Negro, 4072 - Centro - Colorado do Oeste - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- CEREJEIRAS -----------------------------
    {
        "nome": "Cartório de Registro de Imóveis e Anexos",
        "municipio": "Cerejeiras",
        "estado": "RO",
        "telefone": "(69) 3342-2440",
        "email": "imoveisprot_cerejeiras@tjro.jus.br",
        "endereco": "Rua Portugal, 2229 - Centro - Cerejeiras - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- PRESIDENTE MÉDICI -----------------------------
    {
        "nome": "Cartório de Registro de Imóveis e Civil das Pessoas Naturais",
        "municipio": "Presidente Medici",
        "estado": "RO",
        "telefone": "(69) 3471-3077",
        "email": "civileimoveis_pmedici@tjro.jus.br",
        "endereco": "Av. 30 de Junho, 2031 - Salas 1, 2 e 3 - Centro - Presidente Medici - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- MACHADINHO D'OESTE -----------------------------
    {
        "nome": "Ofício de Registro de Imóveis e Anexos - Tabelionato de Protesto",
        "municipio": "Machadinho d'Oeste",
        "estado": "RO",
        "telefone": "(69) 3581-3227",
        "email": "cartoriolilianmdo@gmail.com",
        "endereco": "Rodovia RO-133, 2682 - Centro - Machadinho d'Oeste - RO",
        "tipo": "Registro de Imóveis",
    },

    # ----------------------------- BURITIS -----------------------------
    {
        "nome": "Ofício de Registro de Imóveis, RTD, RCPJ e Protesto",
        "municipio": "Buritis",
        "estado": "RO",
        "telefone": "(69) 3238-2614",
        "email": "imoveisprot_buritis@tjro.jus.br",
        "endereco": "Rua Cacaulândia, 1309 - Setor 02 - Buritis - RO",
        "tipo": "Registro de Imóveis",
    },
]


# -------------------------------------------------------------------
# FUNÇÃO SEEDER
# -------------------------------------------------------------------
def seed_cartorios():
    db = SessionLocal()

    try:
        count = db.query(Cartorio).count()
        if count > 0:
            print(f"⚠️ Já existem {count} cartórios cadastrados. Seed ignorado.")
            return

        for data in CARTORIOS_DATA:
            cart = Cartorio(**data)
            db.add(cart)

        db.commit()

        print(f"✅ Seeder concluído com sucesso: {len(CARTORIOS_DATA)} cartórios inseridos!")

    except Exception as e:
        print("❌ Erro ao executar o seeder:", e)

    finally:
        db.close()


# -------------------------------------------------------------------
# EXECUÇÃO DIRETA
# -------------------------------------------------------------------
if __name__ == "__main__":
    seed_cartorios()
