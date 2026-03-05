def resolve_project_folder(doc_type: str):

    doc_type = doc_type.upper()

    mapping = {

        "CERTIDAO":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/CERTIDOES",

        "MATRICULA":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/CERTIDOES",

        "CCIR":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/CCIR",

        "CAR":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/CAR",

        "ITR":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/ITR",

        "MAPA":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/MAPAS",

        "DOCUMENTO_PESSOAL":
            "DADOS_DO_IMOVEL_GEOREFERENCIADO/PESSOAIS_PROPRIETARIO",

        "ART":
            "PECAS_TECNICAS/ART",

        "MAPA_CERTIFICADO":
            "PECAS_TECNICAS/MAPAS_CERTIFICADOS",

        "REQUERIMENTO":
            "OUTROS/REQUERIMENTOS",

    }

    return mapping.get(
        doc_type,
        "DADOS_DO_IMOVEL_GEOREFERENCIADO/DOCUMENTOS",
    )