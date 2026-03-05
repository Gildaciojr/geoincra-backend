from pathlib import Path

BASE_PROJECT_PATH = Path("/app/app/uploads/projects")


def create_project_structure(project_id: int):

    root = BASE_PROJECT_PATH / f"project_{project_id}"

    folders = [

        # =================================================
        # DADOS DO IMÓVEL GEOREFERENCIADO
        # =================================================
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/DOCUMENTOS",
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/PESSOAIS_PROPRIETARIO",
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/CERTIDOES",
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/MAPAS",
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/CCIR",
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/CAR",
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/ITR",

        # =================================================
        # CONFRONTANTES
        # =================================================
        "DADOS_IMOVEIS_CONFRONTANTES/IMOVEL_01/DOCUMENTOS",
        "DADOS_IMOVEIS_CONFRONTANTES/IMOVEL_01/PESSOAIS_PROPRIETARIO",
        "DADOS_IMOVEIS_CONFRONTANTES/IMOVEL_01/CERTIDOES",
        "DADOS_IMOVEIS_CONFRONTANTES/IMOVEL_01/MAPAS",

        # =================================================
        # CONTRATANTE
        # =================================================
        "CONTRATANTE",

        # =================================================
        # PEÇAS TÉCNICAS
        # =================================================
        "PECAS_TECNICAS/ART",
        "PECAS_TECNICAS/MAPAS_CERTIFICADOS",

        # =================================================
        # OUTROS
        # =================================================
        "OUTROS/REQUERIMENTOS",
    ]

    for folder in folders:
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)