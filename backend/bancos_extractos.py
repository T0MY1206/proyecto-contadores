"""
Configuración de bancos para archivos de extractos.

El sistema soporta únicamente dos bancos: Santander y Banco Provincia.
Cada uno tiene su propio mapeo de columnas (fecha, concepto, monto)
para respetar el formato de exportación de cada banco.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Columnas "firma" por banco: si el archivo tiene alguna de estas columnas (en minúsculas),
# se considera que corresponde a ese banco. Sirve para validar que el usuario eligió el banco correcto.
SIGNATURAS_BANCO: Dict[str, List[str]] = {
    "santander": ["fecha valor", "f_extracto", "fecha comp"],
    "provincia": ["fecha movimiento", "haber", "debe", "orden_pago", "nro_movimiento"],
}

# Clave = id del banco (para API y frontend), valor = listas de posibles nombres de columnas
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


def detectar_banco_por_headers(headers: List[str]) -> str | None:
    """
    Si los headers del Excel tienen columnas firma de un solo banco, devuelve su id.
    Si coinciden con ambos o con ninguno, devuelve None (no se puede determinar).
    """
    headers_lower = {str(h).strip().lower() for h in headers if h}
    encontrados = []
    for banco_id, signaturas in SIGNATURAS_BANCO.items():
        if any(s in headers_lower for s in signaturas):
            encontrados.append(banco_id)
    if len(encontrados) == 1:
        return encontrados[0]
    return None


def get_bancos_lista() -> List[Dict[str, str]]:
    """Devuelve la lista de bancos para el frontend: [{ id, nombre }, ...]."""
    return [
        {"id": banco_id, "nombre": data["nombre"]}
        for banco_id, data in BANCOS_EXTRACTOS.items()
    ]
