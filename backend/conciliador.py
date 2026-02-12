"""
Lógica principal de conciliación contable entre dos archivos de Excel.

Este módulo utiliza pandas para leer los datos y aplicar reglas de
comparación basadas en fechas y montos.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List

import pandas as pd

from .normalizador import normalizar_concepto, normalizar_fecha, normalizar_monto


@dataclass
class ColumnConfig:
    """
    Configuración esperada de columnas en los archivos de entrada.

    Permitimos cierta flexibilidad en los nombres de columna buscando
    equivalentes comunes en minúsculas.
    """

    fecha: str
    concepto: str
    monto: str


def _inferir_columnas(df: pd.DataFrame) -> ColumnConfig:
    """
    Intenta inferir los nombres de las columnas principales (fecha, concepto, monto)
    a partir de los nombres presentes en el DataFrame.
    """
    cols_lower = {c.lower(): c for c in df.columns}

    def buscar(posibles: List[str]) -> str:
        for candidato in posibles:
            if candidato in cols_lower:
                return cols_lower[candidato]
        raise ValueError(
            f"No se encontró ninguna de las columnas requeridas: {', '.join(posibles)}"
        )

    fecha = buscar([
        "fecha", "fecha gasto", "fecha_contable", "f_gasto", "f_contable",
        "fecha ato", "fecha comp", "fecha valor",
    ])
    concepto = buscar([
        "concepto", "descripcion", "detalle", "concepto gasto", "concepto contable",
        "nombre_cuenta",
    ])
    monto = buscar([
        "monto", "importe", "valor", "monto gasto", "monto contable",
        "neto", "importe_debe", "importe_haber",
    ])

    return ColumnConfig(fecha=fecha, concepto=concepto, monto=monto)


def leer_excel_en_memoria(file_bytes: bytes) -> pd.DataFrame:
    """
    Lee un archivo Excel desde bytes y devuelve un DataFrame de pandas.

    - Usa la primera hoja por defecto.
    - Confía en pandas para detectar encabezados.
    """
    buffer = BytesIO(file_bytes)
    df = pd.read_excel(buffer, engine="openpyxl")
    if df.empty:
        raise ValueError("El archivo Excel no contiene filas de datos.")
    return df


def _preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica normalizaciones de fecha, concepto y monto sobre un DataFrame genérico.
    """
    config = _inferir_columnas(df)

    df = df.copy()
    df.rename(
        columns={
            config.fecha: "fecha",
            config.concepto: "concepto",
            config.monto: "monto",
        },
        inplace=True,
    )

    # Normalización de columnas clave
    df["fecha_norm"] = df["fecha"].apply(normalizar_fecha)
    df["concepto_norm"] = df["concepto"].apply(normalizar_concepto)
    df["monto_norm"] = df["monto"].apply(normalizar_monto)

    # Filtramos filas que no tengan datos mínimos válidos
    df = df[
        df["fecha_norm"].notna()
        & df["concepto_norm"].astype(str).str.len().gt(0)
        & df["monto_norm"].notna()
    ].reset_index(drop=True)

    return df


def comparar_movimientos(
    gastos_df: pd.DataFrame,
    contable_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Compara los movimientos de dos DataFrames por fecha y monto.

    Regla: fecha igual Y monto igual = OK (coinciden).
    Devuelve los movimientos que no encuentran contraparte en el otro archivo.
    """
    gastos = _preparar_dataframe(gastos_df)
    contable = _preparar_dataframe(contable_df)

    gastos["id_gasto"] = gastos.index
    contable["id_contable"] = contable.index

    # Índices de filas que ya fueron emparejadas (match fecha + monto)
    usados_gasto: set[int] = set()
    usados_contable: set[int] = set()

    # Emparejamiento 1:1 por (fecha, monto)
    for _, gasto_row in gastos.iterrows():
        id_g = int(gasto_row["id_gasto"])
        if id_g in usados_gasto:
            continue

        candidatos = contable[
            (~contable["id_contable"].isin(usados_contable))
            & (contable["fecha_norm"] == gasto_row["fecha_norm"])
            & (contable["monto_norm"] == gasto_row["monto_norm"])
        ]

        if not candidatos.empty:
            # Tomamos el primero disponible (cualquiera da igual, fecha y monto coinciden)
            id_c = int(candidatos.iloc[0]["id_contable"])
            usados_gasto.add(id_g)
            usados_contable.add(id_c)

    # Movimientos que difieren: sin contraparte
    solo_en_gastos: List[Dict[str, Any]] = []
    solo_en_contable: List[Dict[str, Any]] = []

    for _, row in gastos.iterrows():
        if int(row["id_gasto"]) in usados_gasto:
            continue
        fecha_val = row["fecha_norm"]
        fecha_str = fecha_val.strftime("%Y-%m-%d") if fecha_val is not None else ""
        solo_en_gastos.append(
            {
                "fecha": fecha_str,
                "monto": float(row["monto_norm"]) if row["monto_norm"] is not None else 0,
                "descripcion": str(row["concepto"]) if row["concepto"] else "",
            }
        )

    for _, row in contable.iterrows():
        if int(row["id_contable"]) in usados_contable:
            continue
        fecha_val = row["fecha_norm"]
        fecha_str = fecha_val.strftime("%Y-%m-%d") if fecha_val is not None else ""
        solo_en_contable.append(
            {
                "fecha": fecha_str,
                "monto": float(row["monto_norm"]) if row["monto_norm"] is not None else 0,
                "descripcion": str(row["concepto"]) if row["concepto"] else "",
            }
        )

    total_gastos = len(gastos)
    total_contable = len(contable)
    coincidencias = len(usados_gasto)

    return {
        "solo_en_gastos": solo_en_gastos,
        "solo_en_contable": solo_en_contable,
        "resumen": {
            "total_gastos": total_gastos,
            "total_contable": total_contable,
            "coincidencias": coincidencias,
            "diferentes_gastos": len(solo_en_gastos),
            "diferentes_contable": len(solo_en_contable),
        },
    }
