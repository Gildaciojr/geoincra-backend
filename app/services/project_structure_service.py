from pathlib import Path
from typing import Any

# =========================================================
# BASE DO STORAGE
# =========================================================
BASE_UPLOAD_PATH = Path("/app/app/uploads").resolve()

PROJECTS_ROOT = BASE_UPLOAD_PATH / "projects"


# =========================================================
# DEFINIÇÃO ÚNICA DA ESTRUTURA DO PROJETO
# =========================================================
PROJECT_FOLDER_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "dados_imovel",
        "label": "1. Dados do Imóvel Georreferenciado",
        "path": "1_dados_imovel_georreferenciado",
        "children": [
            {"key": "documentos", "label": "Documentos", "path": "1_dados_imovel_georreferenciado/documentos"},
            {"key": "pessoais_proprietario", "label": "Pessoais do Proprietário", "path": "1_dados_imovel_georreferenciado/pessoais_proprietario"},
            {"key": "certidoes", "label": "Certidões / Matrículas", "path": "1_dados_imovel_georreferenciado/certidoes"},
            {"key": "mapas", "label": "Mapas", "path": "1_dados_imovel_georreferenciado/mapas"},
            {"key": "ccir", "label": "CCIR", "path": "1_dados_imovel_georreferenciado/ccir"},
            {"key": "car", "label": "CAR", "path": "1_dados_imovel_georreferenciado/car"},
            {"key": "itr", "label": "ITR", "path": "1_dados_imovel_georreferenciado/itr"},
        ],
    },
    {
        "key": "confrontantes",
        "label": "2. Dados dos Imóveis Confrontantes",
        "path": "2_dados_imoveis_confrontantes",
        "children": [
            {"key": "imovel_01", "label": "Imóvel 01", "path": "2_dados_imoveis_confrontantes/imovel_01"},
            {"key": "imovel_02", "label": "Imóvel 02", "path": "2_dados_imoveis_confrontantes/imovel_02"},
            {"key": "imovel_03", "label": "Imóvel 03", "path": "2_dados_imoveis_confrontantes/imovel_03"},
            {"key": "imovel_04", "label": "Imóvel 04", "path": "2_dados_imoveis_confrontantes/imovel_04"},
        ],
    },
    {
        "key": "contratante",
        "label": "3. Contratante",
        "path": "3_contratante",
        "children": [],
    },
    {
        "key": "pecas_tecnicas",
        "label": "4. Peças Técnicas",
        "path": "4_pecas_tecnicas",
        "children": [
            {"key": "art", "label": "ART", "path": "4_pecas_tecnicas/art"},
            {"key": "mapas", "label": "Mapas", "path": "4_pecas_tecnicas/mapas"},
            {"key": "requerimentos", "label": "Requerimentos", "path": "4_pecas_tecnicas/requerimentos"},
        ],
    },
    {
        "key": "documentos_processados",
        "label": "5. Documentos Processados",
        "path": "5_documentos_processados",
        "children": [],
    },
]


DOC_TYPE_FOLDER_MAP = {
    "CERTIDAO": "1_dados_imovel_georreferenciado/certidoes",
    "MATRICULA": "1_dados_imovel_georreferenciado/certidoes",
    "CCIR": "1_dados_imovel_georreferenciado/ccir",
    "CAR": "1_dados_imovel_georreferenciado/car",
    "ITR": "1_dados_imovel_georreferenciado/itr",
    "MAPA": "1_dados_imovel_georreferenciado/mapas",
    "PLANTA_MEMORIAL": "1_dados_imovel_georreferenciado/mapas",
    "DOCUMENTO_PESSOAL": "1_dados_imovel_georreferenciado/pessoais_proprietario",
    "CPF_RG": "1_dados_imovel_georreferenciado/pessoais_proprietario",
    "COMPROVANTE_RESIDENCIA": "3_contratante",
    "CONTRATO_PARTICULAR": "3_contratante",
    "ART": "4_pecas_tecnicas/art",
    "TECNICO": "4_pecas_tecnicas/mapas",
    "MAPA_CERTIFICADO": "4_pecas_tecnicas/mapas",
    "REQUERIMENTO": "4_pecas_tecnicas/requerimentos",
    "OUTROS": "1_dados_imovel_georreferenciado/documentos",
}


LEGACY_FOLDER_ALIASES = {
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/DOCUMENTOS": "1_dados_imovel_georreferenciado/documentos",
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/CERTIDOES": "1_dados_imovel_georreferenciado/certidoes",
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/CCIR": "1_dados_imovel_georreferenciado/ccir",
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/CAR": "1_dados_imovel_georreferenciado/car",
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/ITR": "1_dados_imovel_georreferenciado/itr",
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/MAPAS": "1_dados_imovel_georreferenciado/mapas",
    "DADOS_DO_IMOVEL_GEOREFERENCIADO/PESSOAIS_PROPRIETARIO": "1_dados_imovel_georreferenciado/pessoais_proprietario",
    "PECAS_TECNICAS/ART": "4_pecas_tecnicas/art",
    "PECAS_TECNICAS/MAPAS_CERTIFICADOS": "4_pecas_tecnicas/mapas",
    "OUTROS/REQUERIMENTOS": "4_pecas_tecnicas/requerimentos",
}


def get_project_folder_paths() -> list[str]:
    paths: list[str] = []

    for folder in PROJECT_FOLDER_DEFINITIONS:
        paths.append(folder["path"])
        for child in folder.get("children") or []:
            paths.append(child["path"])

    return paths


def normalize_project_folder_path(folder_path: str | None) -> str:
    if not folder_path:
        return "1_dados_imovel_georreferenciado/documentos"

    normalized = str(folder_path).strip().replace("\\", "/").strip("/")
    legacy_key = normalized.upper()

    return LEGACY_FOLDER_ALIASES.get(legacy_key, normalized)


def build_project_folder_tree(project_id: int, documents: list[Any] | None = None) -> dict[str, Any]:
    documents = documents or []
    project_prefix = f"projects/project_{project_id}/"

    def _clone_folder(folder: dict[str, Any]) -> dict[str, Any]:
        return {
            "key": folder["key"],
            "label": folder["label"],
            "path": folder["path"],
            "documents": [],
            "children": [_clone_folder(child) for child in folder.get("children") or []],
        }

    folders = [_clone_folder(folder) for folder in PROJECT_FOLDER_DEFINITIONS]
    by_path: dict[str, dict[str, Any]] = {}

    def _index(folder: dict[str, Any]) -> None:
        by_path[folder["path"]] = folder
        for child in folder.get("children") or []:
            _index(child)

    for folder in folders:
        _index(folder)

    unknown_documents: list[dict[str, Any]] = []

    for doc in documents:
        file_path = getattr(doc, "file_path", None) or ""
        relative_path = str(file_path).replace("\\", "/")

        if relative_path.startswith(project_prefix):
            relative_path = relative_path[len(project_prefix):]

        folder_path = normalize_project_folder_path(str(Path(relative_path).parent).replace("\\", "/"))

        item = {
            "id": getattr(doc, "id", None),
            "doc_type": getattr(doc, "doc_type", None),
            "stored_filename": getattr(doc, "stored_filename", None),
            "original_filename": getattr(doc, "original_filename", None),
            "content_type": getattr(doc, "content_type", None),
            "description": getattr(doc, "description", None),
            "file_path": getattr(doc, "file_path", None),
            "uploaded_at": getattr(doc, "uploaded_at", None),
            "matricula_id": getattr(doc, "matricula_id", None),
        }

        target = by_path.get(folder_path)
        if target:
            target["documents"].append(item)
        else:
            unknown_documents.append(item)

    return {
        "project_id": project_id,
        "folders": folders,
        "unknown_documents": unknown_documents,
    }


# =========================================================
# CRIAR ESTRUTURA DE PASTAS DO PROJETO
# =========================================================
def create_project_structure(project_id: int):

    root = PROJECTS_ROOT / f"project_{project_id}"

    # garante raiz
    root.mkdir(parents=True, exist_ok=True)

    # cria subpastas
    for folder in get_project_folder_paths():
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)
