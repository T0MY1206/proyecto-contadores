"""
Lógica principal de conciliación contable entre dos archivos de Excel.

Lee Excel con openpyxl y compara por fecha y monto (sin pandas).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional

from openpyxl import load_workbook

from .normalizador import normalizar_concepto, normalizar_fecha, normalizar_monto


@dataclass
class ColumnConfig:
    fecha: str
    concepto: str
    monto: str
    monto_creditos: Optional[str] = None
    monto_debitos: Optional[str] = None


def _inferir_columnas(columnas: List[str]) -> ColumnConfig:
    cols_lower = {c.strip().lower() if c else "": c for c in columnas if c is not None}
    cols_lower = {k: v for k, v in cols_lower.items() if k}

    def buscar(posibles: List[str]) -> str:
        for candidato in posibles:
            if candidato in cols_lower:
                return cols_lower[candidato]
        raise ValueError(
            f"No se encontró ninguna de las columnas requeridas: {', '.join(posibles)}"
        )

    def buscar_opt(posibles: List[str]) -> Optional[str]:
        for candidato in posibles:
            if candidato in cols_lower:
                return cols_lower[candidato]
        return None

    fecha = buscar([
        "fecha", "fecha extracto", "fecha gasto", "fecha_contable", "fecha_acreditacion",
        "f_extracto", "f_gasto", "f_contable", "fecha ato", "fecha comp", "fecha valor",
    ])
    concepto = buscar([
        "concepto", "descripcion", "detalle", "movimiento",
        "concepto extracto", "concepto gasto", "concepto contable", "nombre_cuenta",
        "orden_pago", "nro_movimiento", "nro_deposito",
    ])
    creditos = buscar_opt(["creditos", "crédito", "credito"])
    debitos = buscar_opt(["debitos", "débito", "debito"])
    if creditos is not None and debitos is not None:
        return ColumnConfig(
            fecha=fecha, concepto=concepto, monto=creditos,
            monto_creditos=creditos, monto_debitos=debitos,
        )
    monto = buscar([
        "monto", "importe", "valor", "monto extracto", "monto gasto", "monto contable",
        "neto", "saldo", "importe_debe", "importe_haber",
    ])
    return ColumnConfig(fecha=fecha, concepto=concepto, monto=monto)


def leer_excel_en_memoria(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Lee un archivo Excel desde bytes y devuelve una lista de diccionarios (una fila por dict).
    Usa la primera hoja. Prueba varias filas como encabezado (0..11) para soportar informes con títulos.
    """
    buffer = BytesIO(file_bytes)
    ultimo_error: Exception | None = None

    for header_row in range(12):
        try:
            buffer.seek(0)
            wb = load_workbook(buffer, read_only=False, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()

            if not rows or len(rows) <= header_row:
                continue

            headers = [str(c).strip() if c is not None else "" for c in rows[header_row]]
            config = _inferir_columnas(headers)

            data_rows = rows[header_row + 1:]
            out = []
            for row in data_rows:
                if not any(v is not None and str(v).strip() for v in row):
                    continue
                fila = dict(zip(headers, row)) if row else {}
                out.append(fila)
            if out:
                return out
        except ValueError as e:
            ultimo_error = e
            continue
        except Exception:
            buffer.seek(0)
            raise

    raise ValueError(
        ultimo_error.args[0] if ultimo_error else "El archivo Excel no contiene filas de datos."
    )


def _preparar_filas(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aplica normalizaciones y filtra filas inválidas."""
    if not filas:
        return []
    headers = list(filas[0].keys())
    config = _inferir_columnas(headers)

    resultado = []
    for idx, fila in enumerate(filas):
        fecha_val = fila.get(config.fecha)
        concepto_val = fila.get(config.concepto)
        fecha_norm = normalizar_fecha(fecha_val)
        concepto_norm = normalizar_concepto(concepto_val)
        if config.monto_creditos is not None and config.monto_debitos is not None:
            cr = normalizar_monto(fila.get(config.monto_creditos)) or 0.0
            db = normalizar_monto(fila.get(config.monto_debitos)) or 0.0
            monto_val = cr - db
            monto_norm = round(monto_val, 2)
        else:
            monto_val = fila.get(config.monto)
            monto_norm = normalizar_monto(monto_val)

        if fecha_norm is None or monto_norm is None:
            continue
        if not (concepto_norm or concepto_norm.strip()):
            continue

        resultado.append({
            "id": idx,
            "fecha": fecha_val,
            "concepto": concepto_val,
            "monto": monto_val,
            "fecha_norm": fecha_norm,
            "concepto_norm": concepto_norm,
            "monto_norm": monto_norm,
        })
    return resultado


def comparar_movimientos(
    extractos_filas: List[Dict[str, Any]],
    contable_filas: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compara movimientos por fecha y monto. Devuelve los que no tienen contraparte.
    """
    extractos = _preparar_filas(extractos_filas)
    contable = _preparar_filas(contable_filas)

    usados_extracto: set[int] = set()
    usados_contable: set[int] = set()

    for ext in extractos:
        id_e = ext["id"]
        if id_e in usados_extracto:
            continue
        for cont in contable:
            if cont["id"] in usados_contable:
                continue
            if ext["fecha_norm"] == cont["fecha_norm"] and ext["monto_norm"] == cont["monto_norm"]:
                usados_extracto.add(id_e)
                usados_contable.add(cont["id"])
                break

    solo_en_extractos: List[Dict[str, Any]] = []
    solo_en_contable: List[Dict[str, Any]] = []

    for row in extractos:
        if row["id"] in usados_extracto:
            continue
        fn = row["fecha_norm"]
        fecha_str = fn.strftime("%Y-%m-%d") if fn else ""
        solo_en_extractos.append({
            "fecha": fecha_str,
            "monto": float(row["monto_norm"]),
            "descripcion": str(row["concepto"]) if row["concepto"] else "",
        })

    for row in contable:
        if row["id"] in usados_contable:
            continue
        fn = row["fecha_norm"]
        fecha_str = fn.strftime("%Y-%m-%d") if fn else ""
        solo_en_contable.append({
            "fecha": fecha_str,
            "monto": float(row["monto_norm"]),
            "descripcion": str(row["concepto"]) if row["concepto"] else "",
        })

    return {
        "solo_en_extractos": solo_en_extractos,
        "solo_en_contable": solo_en_contable,
        "resumen": {
            "total_extractos": len(extractos),
            "total_contable": len(contable),
            "coincidencias": len(usados_extracto),
            "diferentes_extractos": len(solo_en_extractos),
            "diferentes_contable": len(solo_en_contable),
        },
    }
