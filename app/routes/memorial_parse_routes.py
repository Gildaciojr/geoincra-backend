from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.memorial_parser_service import MemorialParserService

router = APIRouter()


class MemorialParseRequest(BaseModel):
    texto: str


@router.post("/memorial/parse")
def parse_memorial(req: MemorialParseRequest):

    try:

        result = MemorialParserService.gerar_geometria(req.texto)

        return result

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )