"""
Funciones de normalización de datos para el proceso de conciliación.

Todas las funciones están pensadas para ser puras y reutilizables,
de forma que puedan aplicarse fácilmente sobre columnas de DataFrames
de pandas.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Optional

import pandas as pd


def normalizar_fecha(valor: Any) -> Optional[pd.Timestamp]:
    """
    Normaliza una fecha a un objeto pandas.Timestamp.

    - Acepta objetos datetime, pandas.Timestamp o cadenas.
    - Para cadenas intenta varios formatos comunes (día/mes/año, etc.).
    - Devuelve None si no es posible interpretar la fecha.
    """
    if pd.isna(valor):
        return None

    # Si ya es un timestamp/fecha
    if isinstance(valor, (pd.Timestamp, datetime)):
        return pd.to_datetime(valor).normalize()

    # Intento como string
    texto = str(valor).strip()
    if not texto:
        return None

    # Intento directo con pandas (maneja muchos formatos)
    try:
        return pd.to_datetime(texto, dayfirst=True, errors="coerce").normalize()
    except Exception:
        return None


def _quitar_tildes(texto: str) -> str:
    """
    Elimina tildes y diacríticos de una cadena usando unicodedata.
    """
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_concepto(valor: Any) -> str:
    """
    Normaliza un concepto de texto.

    - Convierte a mayúsculas.
    - Elimina tildes.
    - Elimina caracteres especiales innecesarios, dejando letras,
      números y algunos separadores básicos.
    - Colapsa espacios múltiples en uno solo.
    """
    if pd.isna(valor):
        return ""

    texto = str(valor)
    texto = texto.strip().upper()
    texto = _quitar_tildes(texto)

    # Reemplazamos todo lo que no sea letra, número o separadores básicos por espacio
    texto = re.sub(r"[^A-Z0-9\s\-\_\.]", " ", texto)
    # Colapsamos espacios múltiples
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_monto(valor: Any) -> Optional[float]:
    """
    Normaliza un monto numérico.

    - Acepta cadenas con separadores de miles y decimales.
    - Interpreta comas como separador decimal cuando corresponde.
    - Devuelve el valor absoluto con dos decimales.
    - Devuelve None si el valor no puede convertirse a número.
    """
    if pd.isna(valor):
        return None

    # Si ya es numérico
    if isinstance(valor, (int, float)):
        return round(abs(float(valor)), 2)

    texto = str(valor).strip()
    if not texto:
        return None

    # Normalizamos formatos típicos: 1.234,56 o 1,234.56
    # Eliminamos espacios
    texto = texto.replace(" ", "")

    # Caso con coma como decimal (más común en entorno contable hispano)
    if "," in texto and "." in texto:
        # Quitamos puntos de miles y convertimos coma a punto decimal
        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")
    elif "," in texto and "." not in texto:
        # Solo coma -> la tratamos como decimal
        texto = texto.replace(",", ".")
    else:
        # Dejar tal cual si solo tiene punto o no tiene separadores
        pass

    try:
        valor_float = float(texto)
    except ValueError:
        return None

    return round(abs(valor_float), 2)
