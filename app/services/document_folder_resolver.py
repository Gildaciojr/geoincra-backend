from __future__ import annotations

from app.services.project_structure_service import (
    DOC_TYPE_FOLDER_MAP,
)


OCR_FOLDER_MAP = {
    "OCR Dados Brutos":
        (
            "1_dados_imovel_georreferenciado/"
            "ocr/dados_brutos"
        ),

    "OCR Documentos Pessoais":
        (
            "1_dados_imovel_georreferenciado/"
            "ocr/documentos_pessoais"
        ),

    "OCR Ficha Cadastral SIG":
        (
            "1_dados_imovel_georreferenciado/"
            "ocr/ficha_sig"
        ),

    "OCR Confrontantes Croqui":
        (
            "1_dados_imovel_georreferenciado/"
            "ocr/confrontantes"
        ),

    "OCR Matrícula":
        (
            "1_dados_imovel_georreferenciado/"
            "ocr/matriculas"
        ),
}


def resolve_project_folder(
    doc_type: str,
) -> str:

    if not doc_type:
        return (
            "1_dados_imovel_georreferenciado/"
            "documentos"
        )

    doc_type_normalizado = (
        str(doc_type)
        .strip()
    )

    # =====================================================
    # OCRs ESPECIALIZADOS
    # =====================================================
    pasta_ocr = OCR_FOLDER_MAP.get(
        doc_type_normalizado
    )

    if pasta_ocr:
        return pasta_ocr

    # =====================================================
    # LEGADO / DOCUMENTOS TÉCNICOS
    # =====================================================
    pasta_legado = DOC_TYPE_FOLDER_MAP.get(
        doc_type_normalizado.upper()
    )

    if pasta_legado:
        return pasta_legado

    # =====================================================
    # FALLBACK
    # =====================================================
    return (
        "1_dados_imovel_georreferenciado/"
        "documentos"
    )