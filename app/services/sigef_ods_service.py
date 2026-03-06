from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Tuple, List

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P

from app.services.sigef_export_service import SigefExportService


class SigefOdsService:

    @staticmethod
    def gerar_ods_sigef(
        geojson: str,
        epsg_origem: int,
        prefixo_vertice: str = "V",
    ) -> Tuple[str, int, dict]:

        csv_str, epsg_utm, metadata = SigefExportService.gerar_csv_sigef(
            geojson=geojson,
            epsg_origem=epsg_origem,
            prefixo_vertice=prefixo_vertice,
        )

        rows = []
        for line in csv_str.strip().split("\n"):
            rows.append(line.split(";"))

        ods = OpenDocumentSpreadsheet()

        table = Table(name="SIGEF")

        for row_data in rows:
            tr = TableRow()
            for cell in row_data:
                tc = TableCell()
                tc.addElement(P(text=str(cell)))
                tr.addElement(tc)
            table.addElement(tr)

        ods.spreadsheet.addElement(table)

        metadata["formato"] = "ODS"

        return ods, epsg_utm, metadata

    @staticmethod
    def salvar_ods_em_disco(
        imovel_id: int,
        ods,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "sigef")
        os.makedirs(folder, exist_ok=True)

        filename = f"planilha_sigef_{ts}.ods"

        path = os.path.join(folder, filename)

        ods.save(path)

        return path