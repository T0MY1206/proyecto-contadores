"""
Punto de entrada del backend FastAPI para el conciliador contable.

Expone un endpoint POST /conciliar que recibe dos archivos Excel
en formato multipart/form-data. Compara por fecha y monto y genera
un Excel con las diferencias en outputs/.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from . import config
from .bancos_extractos import BANCOS_EXTRACTOS, get_bancos_lista
from .conciliador import comparar_movimientos, leer_excel_en_memoria, preparar_filas_extractos
from .schemas import ErrorResponse


app = FastAPI(
    title="Conciliador Contable",
    description="API para conciliación contable basada en archivos Excel.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=str(exc.detail)).dict(),
    )


@app.post(
    "/conciliar",
    responses={
        200: {"description": "JSON con los movimientos que difieren entre ambos Excels."},
        400: {"model": ErrorResponse, "description": "Error de validación o entrada."},
        500: {"model": ErrorResponse, "description": "Error interno del servidor."},
    },
)
async def conciliar_endpoint(
    extractos_file: UploadFile = File(..., description="Archivo Excel con los extractos."),
    contable_file: UploadFile = File(..., description="Archivo Excel con el registro contable."),
    banco_extractos: str = Form(..., description="Banco del extracto (santander o provincia)."),
    tiene_cheques_diferidos: bool = Form(
        False,
        description="Indica si el extracto tiene una hoja específica de cheques diferidos.",
    ),
    pagina_cheques_diferidos: int | None = Form(
        None,
        description="Número de hoja (1-based) donde están los cheques diferidos.",
    ),
):
    if not extractos_file or not contable_file:
        raise HTTPException(status_code=400, detail="Debe enviar ambos archivos: extractos y contable.")
    # Solo se valida que esté seleccionado un tipo de extracto en el combo; no se inspecciona el archivo.
    if not banco_extractos or banco_extractos not in BANCOS_EXTRACTOS:
        raise HTTPException(
            status_code=400,
            detail="Seleccioná el tipo de extracto (Santander o Banco Provincia) en el combo.",
        )

    if tiene_cheques_diferidos and not pagina_cheques_diferidos:
        raise HTTPException(
            status_code=400,
            detail=(
                "Si marcás que el extracto tiene cheques diferidos, "
                "tenés que indicar en qué hoja están."
            ),
        )

    try:
        extractos_bytes = await extractos_file.read()
        contable_bytes = await contable_file.read()

        if not extractos_bytes:
            raise HTTPException(status_code=400, detail="El archivo de extractos está vacío.")
        if not contable_bytes:
            raise HTTPException(status_code=400, detail="El archivo contable está vacío.")

        try:
            if tiene_cheques_diferidos and pagina_cheques_diferidos is not None:
                # Comparar 2 hojas vs contable: hoja 1 (extracto) + hoja de cheques diferidos
                extractos_principal = leer_excel_en_memoria(
                    extractos_bytes,
                    banco_extractos_id=banco_extractos,
                    sheet_index=1,
                )
                extractos_cheques = leer_excel_en_memoria(
                    extractos_bytes,
                    banco_extractos_id=None,
                    sheet_index=pagina_cheques_diferidos,
                )
                prep_principal = preparar_filas_extractos(
                    extractos_principal, banco_extractos_id=banco_extractos
                )
                prep_cheques = preparar_filas_extractos(
                    extractos_cheques, banco_extractos_id=None
                )
                # Unir y reasignar ids únicos
                extractos_combinados = prep_principal + prep_cheques
                for i, row in enumerate(extractos_combinados):
                    row["id"] = i
                extractos_filas = None  # no se usa; pasamos extractos_preparados
            else:
                extractos_combinados = None
                extractos_filas = leer_excel_en_memoria(
                    extractos_bytes,
                    banco_extractos_id=banco_extractos,
                    sheet_index=None,
                )
            contable_filas = leer_excel_en_memoria(contable_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="No fue posible leer uno de los archivos Excel. Verifique que el formato sea válido (.xlsx).",
            )

        if extractos_combinados is not None:
            resultado = comparar_movimientos(
                [], contable_filas, extractos_preparados=extractos_combinados
            )
        else:
            resultado = comparar_movimientos(
                extractos_filas, contable_filas, extractos_banco_id=banco_extractos
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparacion_{timestamp}.xlsx"
        output_path = config.OUTPUTS_DIR / filename

        font_cuerpo = Font(name="Calibri", size=14)
        font_titulo = Font(name="Calibri", size=14, bold=True)

        def formatear_hoja(ws):
            for row in ws.iter_rows():
                for cell in row:
                    cell.font = font_cuerpo
            for cell in ws[1]:
                cell.font = font_titulo
            for col in ws.columns:
                max_len = max((len(str(c.value or "")) for c in col), default=0)
                if col:
                    ws.column_dimensions[col[0].column_letter].width = min(max_len + 1, 80)

        wb = Workbook()
        ws1 = wb.active
        ws1.title = "Solo en extractos"
        ws1.append(["Fecha", "Monto", "Descripción"])
        for r in resultado["solo_en_extractos"]:
            ws1.append([r["fecha"], r["monto"], r["descripcion"]])
        formatear_hoja(ws1)

        ws2 = wb.create_sheet("Solo en contable")
        ws2.append(["Fecha", "Monto", "Descripción"])
        for r in resultado["solo_en_contable"]:
            ws2.append([r["fecha"], r["monto"], r["descripcion"]])
        formatear_hoja(ws2)

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        output_path.write_bytes(buffer.read())

        resultado["excel_filename"] = filename
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al comparar los archivos: {e}",
        )


@app.get("/descargar/{filename}")
async def descargar_excel(filename: str):
    if not filename.endswith(".xlsx") or ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido.")
    path = config.OUTPUTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="El archivo no existe o ya fue eliminado.")
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


@app.get("/bancos")
async def listar_bancos():
    """Devuelve la lista de bancos disponibles para el archivo de extractos."""
    return {"bancos": get_bancos_lista()}


@app.post(
    "/info_extracto",
    responses={
        200: {"description": "Información básica del archivo de extractos (cantidad de hojas)."},
        400: {"model": ErrorResponse, "description": "Error de validación o entrada."},
    },
)
async def info_extracto(
    extractos_file: UploadFile = File(..., description="Archivo Excel con los extractos."),
):
    """Devuelve la cantidad de hojas del Excel de extractos y sus nombres."""
    if not extractos_file:
        raise HTTPException(status_code=400, detail="Debe enviar un archivo de extractos.")

    contenido = await extractos_file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de extractos está vacío.")

    try:
        buffer = BytesIO(contenido)
        wb = load_workbook(buffer, read_only=True, data_only=True)
        nombres = list(wb.sheetnames)
        wb.close()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="No fue posible leer el archivo de extractos. Verifique que el formato sea válido (.xlsx).",
        )

    return {
        "total_hojas": len(nombres),
        "hojas": [
            {"indice": idx + 1, "nombre": nombre}
            for idx, nombre in enumerate(nombres)
        ],
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Sirve el frontend estático (para despliegue en Render; en local opcional).
if config.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.PORT, reload=True)
