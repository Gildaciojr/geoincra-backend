from app.services.project_structure_service import DOC_TYPE_FOLDER_MAP


def resolve_project_folder(doc_type: str):

    doc_type = doc_type.upper()

    return DOC_TYPE_FOLDER_MAP.get(
        doc_type,
        "1_dados_imovel_georreferenciado/documentos",
    )
