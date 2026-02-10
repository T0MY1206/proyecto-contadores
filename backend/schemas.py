"""
Modelos Pydantic usados por la API.

Se definen principalmente para respuestas de error y metadatos
que pueda necesitar el frontend.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Esquema genérico para devolver errores en formato JSON."""

    detail: str


class ConciliacionMeta(BaseModel):
    """
    Información básica sobre un archivo de conciliación generado.
    """

    filename: str
    url: str
