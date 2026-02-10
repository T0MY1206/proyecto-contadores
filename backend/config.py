"""
Módulo de configuración básica de la aplicación.

Todos los valores de configuración se centralizan aquí para
facilitar su modificación futura.
"""

from pathlib import Path


# Puerto por defecto para el servidor FastAPI/uvicorn.
# Nota: puede ser sobreescrito por la línea de comandos de uvicorn.
PORT: int = 8000

# Carpeta donde se guardarán los archivos de salida de conciliación.
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR: Path = BASE_DIR / "outputs"

# Aseguramos que la carpeta de outputs exista al iniciar el módulo.
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
