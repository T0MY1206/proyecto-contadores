"""
Funciones de normalización de datos para el proceso de conciliación.

Sin dependencia de pandas; solo Python estándar y openpyxl donde haga falta.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Optional


def _is_na(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and valor != valor:  # NaN
        return True
    return False


def normalizar_fecha(valor: Any) -> Optional[datetime]:
    """
    Normaliza una fecha a datetime (solo fecha, hora a 00:00:00).

    - Acepta objetos datetime o cadenas.
    - Para cadenas intenta varios formatos comunes (día/mes/año, etc.).
    - Devuelve None si no es posible interpretar la fecha.
    """
    if _is_na(valor):
        return None

    if isinstance(valor, datetime):
        return valor.replace(hour=0, minute=0, second=0, microsecond=0)

    texto = str(valor).strip()
    if not texto:
        return None

    # Formatos habituales (día primero para uso hispano)
    formatos = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%y", "%d-%m-%y",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            continue
    return None


def _quitar_tildes(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_concepto(valor: Any) -> str:
    """
    Normaliza un concepto de texto: mayúsculas, sin tildes, sin caracteres raros.
    """
    if _is_na(valor):
        return ""

    texto = str(valor).strip().upper()
    texto = _quitar_tildes(texto)
    texto = re.sub(r"[^A-Z0-9\s\-\_\.]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_monto(valor: Any) -> Optional[float]:
    """
    Normaliza un monto: acepta cadenas con coma/punto, devuelve valor absoluto con 2 decimales.
    """
    if _is_na(valor):
        return None

    if isinstance(valor, (int, float)) and not (isinstance(valor, float) and valor != valor):
        return round(abs(float(valor)), 2)

    texto = str(valor).strip().replace(" ", "")
    if not texto:
        return None

    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")

    try:
        return round(abs(float(texto)), 2)
    except ValueError:
        return None
