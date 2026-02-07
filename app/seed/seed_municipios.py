# app/seed/seed_municipios.py

from app.core.database import SessionLocal
from app.models.municipio import Municipio

MUNICIPIOS_DATA = [
    {"nome": "Alta Floresta d'Oeste", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "Alto Alegre dos Parecis", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "Alto Paraíso", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Alvorada d'Oeste", "estado": "RO", "vti_min": 5327.16, "vtn_min": 3729.01},
    {"nome": "Ariquemes", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Buritis", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Cabixi", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Cacaulândia", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Cacoal", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Campo Novo de Rondônia", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Candeias do Jamari", "estado": "RO", "vti_min": 4232.41, "vtn_min": 2962.69},
    {"nome": "Castanheiras", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "Cerejeiras", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Chupinguaia", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Colorado do Oeste", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Corumbiara", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Costa Marques", "estado": "RO", "vti_min": 5327.16, "vtn_min": 3729.01},
    {"nome": "Cujubim", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Espigão d'Oeste", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Governador Jorge Teixeira", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Guajará-Mirim", "estado": "RO", "vti_min": 4138.53, "vtn_min": 2896.97},
    {"nome": "Itapuã do Oeste", "estado": "RO", "vti_min": 4197.33, "vtn_min": 2938.13},
    {"nome": "Jaru", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Ji-Paraná", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Machadinho d'Oeste", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Ministro Andreazza", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Mirante da Serra", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Monte Negro", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Nova Brasilândia d'Oeste", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "Nova Mamoré", "estado": "RO", "vti_min": 4138.53, "vtn_min": 2896.97},
    {"nome": "Nova União", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Novo Horizonte do Oeste", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "Ouro Preto do Oeste", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Parecis", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Pimenta Bueno", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Pimenteiras do Oeste", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Porto Velho (Alto Madeira)", "estado": "RO", "vti_min": 4082.65, "vtn_min": 2857.85},
    {"nome": "Porto Velho (Baixo Madeira)", "estado": "RO", "vti_min": 3290.63, "vtn_min": 2303.44},
    {"nome": "Porto Velho (Ponta do Abunã)", "estado": "RO", "vti_min": 3740.14, "vtn_min": 2618.10},
    {"nome": "Presidente Médici", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Primavera de Rondônia", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
    {"nome": "Rio Crespo", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Rolim de Moura", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "Santa Luzia d'Oeste", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "São Felipe d'Oeste", "estado": "RO", "vti_min": 6095.33, "vtn_min": 4266.73},
    {"nome": "São Francisco do Guaporé", "estado": "RO", "vti_min": 5327.16, "vtn_min": 3729.01},
    {"nome": "São Miguel do Guaporé", "estado": "RO", "vti_min": 5327.16, "vtn_min": 3729.01},
    {"nome": "Seringueiras", "estado": "RO", "vti_min": 5327.16, "vtn_min": 3729.01},
    {"nome": "Teixeirópolis", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Theobroma", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Urupá", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Vale do Anari", "estado": "RO", "vti_min": 6196.05, "vtn_min": 4337.24},
    {"nome": "Vale do Paraíso", "estado": "RO", "vti_min": 6846.59, "vtn_min": 4792.61},
    {"nome": "Vilhena", "estado": "RO", "vti_min": 4687.33, "vtn_min": 3281.13},
]

def seed_municipios():
    db = SessionLocal()
    try:
        existentes = {m.nome for m in db.query(Municipio).all()}
        novos = 0

        for item in MUNICIPIOS_DATA:
            if item["nome"] in existentes:
                continue

            m = Municipio(
                nome=item["nome"],
                estado=item["estado"],
                vti_min=item["vti_min"],
                vtn_min=item["vtn_min"],
            )
            db.add(m)
            novos += 1

        if novos:
            db.commit()

        print(f"Seed municipios concluído. Inseridos: {novos}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_municipios()
