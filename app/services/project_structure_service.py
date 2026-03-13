from pathlib import Path

# =========================================================
# BASE DO STORAGE
# =========================================================
BASE_UPLOAD_PATH = Path("/app/app/uploads").resolve()

PROJECTS_ROOT = BASE_UPLOAD_PATH / "projects"


# =========================================================
# CRIAR ESTRUTURA DE PASTAS DO PROJETO
# =========================================================
def create_project_structure(project_id: int):

    root = PROJECTS_ROOT / f"project_{project_id}"

    folders = [

        # =================================================
        # 1️⃣ DADOS DO IMÓVEL GEOREFERENCIADO
        # =================================================
        "1_dados_imovel_georreferenciado/documentos",
        "1_dados_imovel_georreferenciado/pessoais_proprietario",
        "1_dados_imovel_georreferenciado/certidoes",
        "1_dados_imovel_georreferenciado/mapas",
        "1_dados_imovel_georreferenciado/ccir",
        "1_dados_imovel_georreferenciado/car",
        "1_dados_imovel_georreferenciado/itr",

        # =================================================
        # 2️⃣ CONFRONTANTES
        # =================================================
        "2_dados_imoveis_confrontantes/imovel_01",
        "2_dados_imoveis_confrontantes/imovel_02",
        "2_dados_imoveis_confrontantes/imovel_03",
        "2_dados_imoveis_confrontantes/imovel_04",

        # =================================================
        # 3️⃣ CONTRATANTE
        # =================================================
        "3_contratante",

        # =================================================
        # 4️⃣ PEÇAS TÉCNICAS
        # =================================================
        "4_pecas_tecnicas/art",
        "4_pecas_tecnicas/mapas",
        "4_pecas_tecnicas/requerimentos",

        # =================================================
        # 5️⃣ DOCUMENTOS PROCESSADOS (IA / OCR)
        # =================================================
        "5_documentos_processados",
    ]

    # garante raiz
    root.mkdir(parents=True, exist_ok=True)

    # cria subpastas
    for folder in folders:
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)