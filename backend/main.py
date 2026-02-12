"""
Punto de entrada del backend FastAPI para el conciliador contable.

Expone un endpoint POST /conciliar que recibe dos archivos Excel
en formato multipart/form-data:
  - extractos_file
  - contable_file

Compara por fecha y monto; devuelve JSON con los movimientos que difieren
y genera un Excel con el resultado en la carpeta outputs.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import config
from .conciliador import comparar_movimientos, leer_excel_en_memoria
from .schemas import ErrorResponse


app = FastAPI(
    title="Conciliador Contable",
    description="API para conciliación contable basada en archivos Excel.",
    version="1.0.0",
)

# Configuración CORS para permitir llamadas desde el frontend (p.ej. file:// o http://localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    """
    Manejador centralizado de errores HTTPException para devolver
    siempre un JSON con el campo 'detail'.
    """
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
):
    """
    Endpoint principal para comparar dos Excels por fecha y monto.

    - Valida que se reciban ambos archivos.
    - Lee los excels en memoria.
    - Compara: fecha igual y monto igual = OK.
    - Devuelve los movimientos que no encuentran contraparte.
    """
    if not extractos_file or not contable_file:
        raise HTTPException(status_code=400, detail="Debe enviar ambos archivos: extractos y contable.")

    try:
        extractos_bytes = await extractos_file.read()
        contable_bytes = await contable_file.read()

        if not extractos_bytes:
            raise HTTPException(status_code=400, detail="El archivo de extractos está vacío.")
        if not contable_bytes:
            raise HTTPException(status_code=400, detail="El archivo contable está vacío.")

        # Lectura de excels en DataFrames
        try:
            extractos_df = leer_excel_en_memoria(extractos_bytes)
            contable_df = leer_excel_en_memoria(contable_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="No fue posible leer uno de los archivos Excel. "
                "Verifique que el formato sea válido (.xlsx).",
            )

        resultado = comparar_movimientos(extractos_df, contable_df)

        # Generar Excel con los movimientos que difieren
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparacion_{timestamp}.xlsx"
        output_path = config.OUTPUTS_DIR / filename

        with BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_extractos = pd.DataFrame(resultado["solo_en_extractos"])
                df_extractos = df_extractos[["fecha", "monto", "descripcion"]] if not df_extractos.empty else pd.DataFrame(
                    columns=["fecha", "monto", "descripcion"]
                )
                df_extractos.columns = ["Fecha", "Monto", "Descripción"]
                df_extractos.to_excel(writer, index=False, sheet_name="Solo en extractos")

                df_contable = pd.DataFrame(resultado["solo_en_contable"])
                df_contable = df_contable[["fecha", "monto", "descripcion"]] if not df_contable.empty else pd.DataFrame(
                    columns=["fecha", "monto", "descripcion"]
                )
                df_contable.columns = ["Fecha", "Monto", "Descripción"]
                df_contable.to_excel(writer, index=False, sheet_name="Solo en contable")
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
    """
    Descarga el archivo Excel de comparación generado.
    """
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


@app.get("/health")
async def health_check():
    """
    Endpoint sencillo para comprobar que la API está viva.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    # Punto de entrada opcional si se ejecuta como script:
    # python -m backend.main
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.PORT, reload=True)
