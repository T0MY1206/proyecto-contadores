"""
Configuración de bancos para archivos de extractos.

El sistema soporta únicamente dos bancos: Santander y Banco Provincia.
Cada uno tiene su propio mapeo de columnas (fecha, concepto, monto).
Se usa el banco que el usuario selecciona en el combo; no se valida el contenido del archivo.
"""

from __future__ import annotations

from typing import Any, Dict, List

# id del banco -> columnas aceptadas para ese formato (1 banco = 1 formato)
BANCOS_EXTRACTOS: Dict[str, Dict[str, Any]] = {
    "santander": {
        "nombre": "Santander",
        "fecha": [
            "fecha valor",
            "fecha",
            "fecha extracto",
            "fecha_contable",
            "f_extracto",
            "fecha comp",
        ],
        "concepto": [
            "concepto",
            "descripcion",
            "detalle",
            "movimiento",
            "concepto extracto",
            "nombre_cuenta",
        ],
        "monto": [
            "monto",
            "importe",
            "valor",
            "monto extracto",
            "neto",
            "saldo",
        ],
        "creditos": ["creditos", "crédito", "credito"],
        "debitos": ["debitos", "débito", "debito"],
    },
    "provincia": {
        "nombre": "Banco Provincia",
        "fecha": [
            "fecha",
            "fecha extracto",
            "fecha movimiento",
            "fecha_contable",
            "fecha valor",
            "f_extracto",
            "f_gasto",
            "f_contable",
            "fecha comp",
        ],
        "concepto": [
            "concepto",
            "descripcion",
            "detalle",
            "movimiento",
            "concepto extracto",
            "concepto contable",
            "nombre_cuenta",
            "orden_pago",
            "nro_movimiento",
        ],
        "monto": [
            "monto",
            "importe",
            "valor",
            "monto extracto",
            "monto contable",
            "neto",
            "saldo",
            "importe_debe",
            "importe_haber",
        ],
        "creditos": ["creditos", "crédito", "credito", "haber"],
        "debitos": ["debitos", "débito", "debito", "debe"],
    },
}


def get_bancos_lista() -> List[Dict[str, str]]:
    """Devuelve la lista de bancos para el frontend: [{ id, nombre }, ...]."""
    return [
        {"id": banco_id, "nombre": data["nombre"]}
        for banco_id, data in BANCOS_EXTRACTOS.items()
    ]
