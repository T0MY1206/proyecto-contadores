"""
Lógica principal de conciliación contable entre dos archivos de Excel.

Este módulo utiliza pandas para leer los datos y aplicar reglas de
conciliación basadas en fechas, montos y similitud de conceptos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz

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

    fecha = buscar(["fecha", "fecha gasto", "fecha_contable", "f_gasto", "f_contable"])
    concepto = buscar(
        ["concepto", "descripcion", "detalle", "concepto gasto", "concepto contable"]
    )
    monto = buscar(["monto", "importe", "valor", "monto gasto", "monto contable"])

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


def _calcular_similitud_concepto(a: str, b: str) -> float:
    """
    Calcula la similitud entre dos conceptos usando la métrica de RapidFuzz.

    Devuelve un porcentaje entre 0 y 100.
    """
    if not a or not b:
        return 0.0
    return float(fuzz.token_sort_ratio(a, b))


def conciliar(
    gastos_df: pd.DataFrame,
    contable_df: pd.DataFrame,
    ventana_dias_posible: int = 3,
    umbral_conciliado: float = 90.0,
    umbral_posible_min: float = 70.0,
    umbral_posible_max: float = 89.99,
) -> pd.DataFrame:
    """
    Realiza la conciliación entre dos DataFrames ya leídos.

    Reglas:
    - Conciliados: fecha idéntica, monto idéntico, concepto similitud ≥ umbral_conciliado.
    - Posibles: fecha ± ventana_dias_posible, monto igual, similitud concepto entre
      [umbral_posible_min, umbral_posible_max].
    - No conciliados: el resto de registros de gastos y contable.
    """
    gastos = _preparar_dataframe(gastos_df)
    contable = _preparar_dataframe(contable_df)

    # Añadimos índices auxiliares para poder identificar filas únicas
    gastos["id_gasto"] = gastos.index
    contable["id_contable"] = contable.index

    # Listas para ir guardando resultados intermedios
    resultados: List[Dict[str, Any]] = []

    # Creamos estructura para marcar contables ya usados
    usados_contable: set[int] = set()

    def registrar_match(
        id_gasto: int,
        id_contable: Optional[int],
        estado: str,
        observacion: str,
    ) -> None:
        """Registra una fila en la salida unificada."""
        gasto_row = gastos.loc[gastos["id_gasto"] == id_gasto].iloc[0]

        if id_contable is not None:
            cont_row = contable.loc[contable["id_contable"] == id_contable].iloc[0]
            usados_contable.add(id_contable)

            fecha_cont = cont_row["fecha_norm"]
            conc_cont = cont_row["concepto"]
            monto_cont = cont_row["monto_norm"]
        else:
            fecha_cont = None
            conc_cont = None
            monto_cont = None

        resultados.append(
            {
                "Fecha gasto": gasto_row["fecha_norm"].date()
                if gasto_row["fecha_norm"] is not None
                else None,
                "Concepto gasto": gasto_row["concepto"],
                "Monto gasto": gasto_row["monto_norm"],
                "Fecha contable": fecha_cont.date() if fecha_cont is not None else None,
                "Concepto contable": conc_cont,
                "Monto contable": monto_cont,
                "Estado": estado,
                "Observaciones": observacion,
            }
        )

    # Paso 1: conciliados exactos
    for _, gasto_row in gastos.iterrows():
        candidatos = contable[
            (contable["id_contable"].isin(usados_contable) == False)
            & (contable["fecha_norm"] == gasto_row["fecha_norm"])
            & (contable["monto_norm"] == gasto_row["monto_norm"])
        ]

        if candidatos.empty:
            continue

        # Elegir el de mayor similitud de concepto
        mejor_id: Optional[int] = None
        mejor_sim = -1.0
        for _, cont_row in candidatos.iterrows():
            sim = _calcular_similitud_concepto(
                gasto_row["concepto_norm"], cont_row["concepto_norm"]
            )
            if sim > mejor_sim:
                mejor_sim = sim
                mejor_id = int(cont_row["id_contable"])

        if mejor_id is not None and mejor_sim >= umbral_conciliado:
            registrar_match(
                id_gasto=int(gasto_row["id_gasto"]),
                id_contable=mejor_id,
                estado="Conciliado",
                observacion=f"Similitud concepto {mejor_sim:.1f}%",
            )

    # Paso 2: conciliaciones posibles para gastos aún no conciliados
    conciliados_ids_gasto = {r["Fecha gasto"] for r in resultados}

    gastos_pendientes = gastos[
        gastos["fecha_norm"].notna()
        & ~gastos["id_gasto"].isin(
            [gastos[gastos["fecha_norm"].dt.date == fg].index[0] for fg in conciliados_ids_gasto]
            if conciliados_ids_gasto
            else []
        )
    ]

    for _, gasto_row in gastos_pendientes.iterrows():
        fecha_min = gasto_row["fecha_norm"] - timedelta(days=ventana_dias_posible)
        fecha_max = gasto_row["fecha_norm"] + timedelta(days=ventana_dias_posible)

        candidatos = contable[
            (contable["id_contable"].isin(usados_contable) == False)
            & (contable["fecha_norm"] >= fecha_min)
            & (contable["fecha_norm"] <= fecha_max)
            & (contable["monto_norm"] == gasto_row["monto_norm"])
        ]

        if candidatos.empty:
            continue

        mejor_id: Optional[int] = None
        mejor_sim = -1.0
        for _, cont_row in candidatos.iterrows():
            sim = _calcular_similitud_concepto(
                gasto_row["concepto_norm"], cont_row["concepto_norm"]
            )
            if sim > mejor_sim:
                mejor_sim = sim
                mejor_id = int(cont_row["id_contable"])

        if (
            mejor_id is not None
            and mejor_sim >= umbral_posible_min
            and mejor_sim <= umbral_posible_max
        ):
            registrar_match(
                id_gasto=int(gasto_row["id_gasto"]),
                id_contable=mejor_id,
                estado="Posible",
                observacion=f"Fecha dentro de ±{ventana_dias_posible} días, similitud {mejor_sim:.1f}%",
            )

    # Paso 3: gastos no conciliados
    ids_gasto_conciliados = {gastos[gastos["fecha_norm"].dt.date == r["Fecha gasto"]].index[0]
                             for r in resultados}
    for _, gasto_row in gastos.iterrows():
        if int(gasto_row["id_gasto"]) in ids_gasto_conciliados:
            continue
        registrar_match(
            id_gasto=int(gasto_row["id_gasto"]),
            id_contable=None,
            estado="No conciliado",
            observacion="No se encontró registro contable coincidente.",
        )

    # Paso 4: contables sobrantes sin gasto asociado
    ids_contable_usados = usados_contable
    for _, cont_row in contable.iterrows():
        if int(cont_row["id_contable"]) in ids_contable_usados:
            continue
        resultados.append(
            {
                "Fecha gasto": None,
                "Concepto gasto": None,
                "Monto gasto": None,
                "Fecha contable": cont_row["fecha_norm"].date()
                if cont_row["fecha_norm"] is not None
                else None,
                "Concepto contable": cont_row["concepto"],
                "Monto contable": cont_row["monto_norm"],
                "Estado": "No conciliado",
                "Observaciones": "Registro contable sin gasto asociado.",
            }
        )

    # Construimos el DataFrame final en el orden solicitado
    df_resultado = pd.DataFrame(resultados)
    columnas_orden = [
        "Fecha gasto",
        "Concepto gasto",
        "Monto gasto",
        "Fecha contable",
        "Concepto contable",
        "Monto contable",
        "Estado",
        "Observaciones",
    ]
    df_resultado = df_resultado[columnas_orden]

    return df_resultado
