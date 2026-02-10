"""
Punto de entrada del backend FastAPI para el conciliador contable.

Expone un endpoint POST /conciliar que recibe dos archivos Excel
en formato multipart/form-data:
  - gastos_file
  - contable_file

Devuelve un archivo Excel con el resultado de la conciliación.
En caso de error, responde con JSON claro y estructurado.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import config
from .conciliador import conciliar, leer_excel_en_memoria
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
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
            "description": "Archivo Excel con el resultado de la conciliación.",
        },
        400: {"model": ErrorResponse, "description": "Error de validación o entrada."},
        500: {"model": ErrorResponse, "description": "Error interno del servidor."},
    },
)
async def conciliar_endpoint(
    gastos_file: UploadFile = File(..., description="Archivo Excel con los gastos."),
    contable_file: UploadFile = File(..., description="Archivo Excel con el registro contable."),
):
    """
    Endpoint principal para realizar la conciliación.

    - Valida que se reciban ambos archivos.
    - Lee los excels en memoria.
    - Ejecuta la lógica de conciliación.
    - Guarda el resultado en la carpeta outputs.
    - Devuelve el archivo Excel resultante.
    """
    if not gastos_file or not contable_file:
        raise HTTPException(status_code=400, detail="Debe enviar ambos archivos: gastos y contable.")

    try:
        gastos_bytes = await gastos_file.read()
        contable_bytes = await contable_file.read()

        if not gastos_bytes:
            raise HTTPException(status_code=400, detail="El archivo de gastos está vacío.")
        if not contable_bytes:
            raise HTTPException(status_code=400, detail="El archivo contable está vacío.")

        # Lectura de excels en DataFrames
        try:
            gastos_df = leer_excel_en_memoria(gastos_bytes)
            contable_df = leer_excel_en_memoria(contable_bytes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="No fue posible leer uno de los archivos Excel. "
                "Verifique que el formato sea válido (.xlsx).",
            )

        # Ejecutamos conciliación
        df_resultado = conciliar(gastos_df, contable_df)

        # Guardamos resultado a disco en carpeta outputs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conciliacion_{timestamp}.xlsx"
        output_path: Path = config.OUTPUTS_DIR / filename

        with BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_resultado.to_excel(writer, index=False, sheet_name="Conciliacion")
            buffer.seek(0)
            output_path.write_bytes(buffer.read())

        # Devolvemos el archivo guardado
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )

    except HTTPException:
        # Re-lanzamos HTTPException para que la maneje el handler configurado
        raise
    except Exception as e:
        # Cualquier otro error se envuelve en un 500 controlado
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al realizar la conciliación: {e}",
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
