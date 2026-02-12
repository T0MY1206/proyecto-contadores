"""
Módulo de configuración básica de la aplicación.

Todos los valores de configuración se centralizan aquí para
facilitar su modificación futura.
"""

import os
from pathlib import Path


# Puerto: en Render se usa la variable PORT; en local, 8000.
PORT: int = int(os.environ.get("PORT", "8000"))

# Carpeta donde se guardarán los archivos de salida de conciliación.
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR: Path = BASE_DIR / "outputs"
FRONTEND_DIR: Path = BASE_DIR / "frontend"

# Aseguramos que la carpeta de outputs exista al iniciar el módulo.
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
