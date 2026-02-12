## Conciliador Contable (FastAPI)

Aplicación para conciliar un Excel de **extractos** con un Excel **contable**. Usa fechas, montos y conceptos y genera un Excel con las diferencias en la carpeta `outputs/`.

---

### Cómo poner en marcha la aplicación (paso a paso)

Ejecutar **estos comandos en orden** en **CMD** (Símbolo del sistema de Windows). La primera vez hacés todo; en las siguientes solo los pasos 1, 3 y 5.

**1. Ir a la carpeta del proyecto**

```cmd
cd c:\Proyectos\proyecto-contable
```

**2. Crear el entorno virtual** (solo la primera vez)

```cmd
python -m venv venv
```

**3. Activar el entorno virtual**

```cmd
venv\Scripts\activate.bat
```

**4. Instalar dependencias** (solo la primera vez, o si cambiás `requirements.txt`)

```cmd
pip install -r requirements.txt
```

**5. Levantar el backend**

```cmd
python -m uvicorn backend.main:app --reload --port 8000
```

Dejá esta ventana de CMD abierta. El backend queda en **http://localhost:8000**.

**Cómo detener el backend**

- **En la misma CMD donde está corriendo:** apretá **Ctrl+C**.
- **Desde otra CMD** (si cerraste la ventana del backend): ejecutá  
  `for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %a`  
  (eso cierra el proceso que usa el puerto 8000).

**6. Abrir el frontend**

- Abrí en el navegador **`frontend/index.html`** (doble clic sobre el archivo),  
- O servilo con una extensión tipo **Live Server** desde la carpeta `frontend/`.

En la página cargás los dos Excels (extractos y contable), hacés clic en **Conciliar** y podés descargar el resultado.

**Cómo verificar que el backend está corriendo**

- **Opción A — Navegador:** abrí **http://localhost:8000/health**. Si ves `{"status":"ok"}` → el backend está bien. Si la página no carga → el backend no está levantado o hay firewall.
- **Opción B — Script:** en **otra** ventana de CMD (con el backend ya corriendo), desde la carpeta del proyecto ejecutá `python verificar_backend.py`. Si dice "OK - El backend esta corriendo" → está bien; si dice "El backend NO esta corriendo" → tenés que levantar el backend en la otra ventana primero.
- **Documentación:** **http://localhost:8000/docs** abre la API interactiva (Swagger).

---

### Requisitos

- **Python 3.11** o superior (se recomienda 3.14 si está disponible).
- `pip` instalado.

Las dependencias están en `requirements.txt` (FastAPI, uvicorn, openpyxl, python-multipart). El proyecto no usa pandas (solo openpyxl y Python estándar) para evitar problemas con DLL bloqueadas en Windows.

---

### Problemas frecuentes

- **"uvicorn no se reconoce como comando"**  
  Usá siempre: `python -m uvicorn backend.main:app --reload --port 8000` (no ejecutes `uvicorn` solo).

- **"DLL load failed..." (Control de aplicaciones)**  
  Este proyecto ya no usa pandas; si actualizaste el código y reinstalaste dependencias (`pip install -r requirements.txt`), ese error no debería aparecer. Si lo ves con otra librería, agregá una exclusión en Windows para la carpeta del proyecto.

---

### Desplegar en Render (con GitHub)

1. Subí el proyecto a un repositorio de **GitHub** (por ejemplo `tu-usuario/proyecto-contable`).

2. Entrá en [render.com](https://render.com), creá una cuenta y **New → Web Service**.

3. Conectá tu cuenta de GitHub y elegí el repositorio del proyecto.

4. Render puede detectar el `render.yaml` del repo. Si lo usás:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Runtime:** Python 3

5. Si no usás el Blueprint, configurá a mano:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

6. Creá el servicio. Render te dará una URL (ej. `https://conciliador-contable.onrender.com`). En esa URL se sirve **todo**: la página de conciliación y la API. No hace falta desplegar el frontend por separado.

**Nota:** En el plan gratuito el disco es efímero: si el servicio “duerme” y volvés más tarde, el botón “Descargar Excel” puede no encontrar el archivo. Conviene descargar el Excel justo después de hacer la conciliación, o volver a comparar y descargar de nuevo.

---

### Formato esperado de los Excels de entrada

Cada archivo debe tener **al menos una hoja** con columnas para:

- **Fecha**
- **Concepto / Descripción**
- **Monto / Importe**

Los nombres pueden variar; la aplicación busca en minúsculas variantes como: `fecha`, `fecha extracto`, `concepto`, `descripcion`, `detalle`, `monto`, `importe`, `valor`. Si falta alguna columna requerida, el backend devuelve un error JSON descriptivo.

---

### Reglas de normalización

En `backend/normalizador.py`:

- **Fechas:** se convierten a `pandas.Timestamp`; formato tipo día/mes/año; se descartan inválidas.
- **Conceptos:** mayúsculas, sin tildes, sin caracteres raros, espacios múltiples colapsados.
- **Montos:** se interpretan formatos con coma/punto (ej. 1.234,56 o 1,234.56); valor absoluto con 2 decimales.

---

### Reglas de conciliación

En `backend/conciliador.py`:

- **Conciliados:** misma fecha y monto; similitud de concepto ≥ 90%.
- **Posibles:** fecha contable ± 3 días, mismo monto, similitud 70–90%.
- **No conciliados:** lo que no cumple lo anterior.

El resultado incluye columnas como Fecha/Concepto/Monto (extracto y contable), Estado y Observaciones.

---

### Carpeta de salida `outputs/`

Cada conciliación exitosa genera un Excel `comparacion_YYYYMMDD_HHMMSS.xlsx` en `outputs/`. La carpeta se crea sola al iniciar el backend (`backend/config.py`).

---

### Errores comunes del API

El backend responde con JSON y campo `detail`, por ejemplo:

- Falta un archivo: `"Debe enviar ambos archivos: extractos y contable."`
- Archivo vacío: mensaje indicando cuál.
- Columnas no detectadas o Excel inválido: mensaje descriptivo.
- Error interno: `"Error interno al comparar los archivos: ..."`

En el frontend estos mensajes se muestran en la zona de estado bajo el formulario.

---

### Estructura del proyecto

```text
proyecto-contable/
├── backend/
│   ├── main.py
│   ├── conciliador.py
│   ├── normalizador.py
│   ├── schemas.py
│   └── config.py
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── outputs/
├── requirements.txt
└── README.md
```
