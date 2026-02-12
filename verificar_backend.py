"""
Script para comprobar si el backend está corriendo.
Ejecutar (con o sin venv activado): python verificar_backend.py
"""
import urllib.request
import urllib.error
import json

URL = "http://127.0.0.1:8000/health"

def main():
    try:
        req = urllib.request.Request(URL)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "ok":
                print("OK - El backend esta corriendo en http://localhost:8000")
                return 0
            print("El backend respondio pero con un formato inesperado:", data)
            return 1
    except urllib.error.URLError as e:
        err = str(e.reason).lower()
        if "refused" in err or "deneg" in err or "10061" in err or "no connection" in err:
            print("ERROR - El backend NO esta corriendo. Inicialo con:")
            print("  venv\\Scripts\\activate.bat")
            print("  python -m uvicorn backend.main:app --port 8000")
        else:
            print("ERROR - No se pudo conectar:", e.reason)
        return 1
    except Exception as e:
        print("ERROR -", e)
        return 1

if __name__ == "__main__":
    exit(main())
