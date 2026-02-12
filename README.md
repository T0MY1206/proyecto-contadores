## Conciliador Contable (FastAPI + Pandas)

Aplicación sencilla para realizar conciliaciones contables entre un Excel de **extractos** y un Excel **contable**, utilizando **Python 3.14**, **FastAPI** y **Pandas**.

La conciliación aplica reglas basadas en fechas, montos y similitud de conceptos, y genera un nuevo archivo Excel en la carpeta `outputs/`.

---

### Requisitos

- **Python 3.14** (o compatible con 3.11+ mientras sale 3.14 estable).
- `pip` instalado.

Dependencias principales (también listadas en `requirements.txt`):

- `fastapi`
- `uvicorn`
- `pandas`
- `openpyxl`
- `python-multipart`
- `rapidfuzz`

---

### Instalación

Desde una terminal, en la carpeta del proyecto `conciliador-contable/`:

1. **Crear entorno virtual**

   ```bash
   python3.14 -m venv venv
   ```

   En Windows PowerShell:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   En Linux/Mac:

   ```bash
   source venv/bin/activate
   ```

2. **Instalar dependencias**

   ```bash
   pip install -r requirements.txt
   ```

---

### Ejecutar el backend

Con el entorno virtual activado, dentro de la carpeta del proyecto:

```bash
uvicorn backend.main:app --reload --port 8000
```

Por defecto el backend quedará accesible en `http://localhost:8000`.

Puedes comprobar que está activo visitando en el navegador:

- `http://localhost:8000/docs` (documentación interactiva Swagger).
- `http://localhost:8000/health` (comprobación rápida).

---

### Abrir el frontend

El frontend es una página estática ubicada en `frontend/`.

Opciones:

- Abrir directamente `frontend/index.html` con el navegador (doble clic).
- O servirlo con algún servidor estático simple (por ejemplo con la extensión de servidor Live Server de tu editor).

La página mostrará:

- Dos campos de carga de archivos (`extractos_file` y `contable_file`).
- Un botón **“Conciliar”**.
- Una zona de mensajes de estado.
- Un botón **“Descargar último resultado”** (se habilita tras la primera conciliación).

Al pulsar **“Conciliar”**, el frontend enviará una petición `POST` a:

- `http://localhost:8000/conciliar`

con ambos archivos en `multipart/form-data`. Si todo es correcto, descargará automáticamente el Excel de conciliación y además permitirá descargarlo de nuevo desde el botón de descarga.

---

### Formato esperado de los Excels de entrada

Cada archivo debe contener **al menos una hoja** con columnas que representen:

- **Fecha**
- **Concepto / Descripción**
- **Monto / Importe**

Los nombres de columna pueden variar, pero la aplicación intenta detectarlos automáticamente buscando, en minúsculas, entre opciones habituales:

- Para la fecha: `fecha`, `fecha extracto`, `fecha_contable`, `f_extracto`, `f_contable`.
- Para el concepto: `concepto`, `descripcion`, `detalle`, `concepto extracto`, `concepto contable`.
- Para el monto: `monto`, `importe`, `valor`, `monto extracto`, `monto contable`.

Si no se encuentra alguna columna requerida, el backend devolverá un error JSON con un mensaje descriptivo.

---

### Reglas de normalización

La lógica de normalización se encuentra en `backend/normalizador.py`:

- **Fechas**
  - Se convierten a `pandas.Timestamp`.
  - Se intenta interpretar el texto con día primero (formato `día/mes/año`).
  - Las fechas inválidas se descartan.

- **Conceptos**
  - Se convierten a mayúsculas.
  - Se eliminan tildes y diacríticos.
  - Se eliminan caracteres especiales innecesarios, dejando letras, números y separadores básicos.
  - Se colapsan espacios múltiples en uno solo.

- **Montos**
  - Se interpretan cadenas con comas y puntos como separadores de miles/decimales.
  - Se considera el formato contable habitual (`1.234,56`, `1,234.56`, etc.).
  - Se toma el **valor absoluto** con **2 decimales**.

---

### Reglas de conciliación

La lógica principal está implementada en `backend/conciliador.py`.

Se generan tres tipos de resultados:

- **Conciliados**
  - Fecha de extracto y fecha contable **idénticas**.
  - Monto de extracto y monto contable **idénticos** (tras normalización).
  - Similitud de concepto **≥ 90%** (utilizando `rapidfuzz`).

- **Posibles conciliaciones**
  - Fecha contable dentro de un rango de **± 3 días** respecto a la fecha de extracto.
  - Monto igual (tras normalización).
  - Similitud de concepto entre **70% y 89.99%**.

- **No conciliados**
  - Registros de extractos que no cumplen ninguna de las condiciones anteriores.
  - Registros contables que no se asignan a ningún extracto.

El DataFrame final contiene las columnas:

- `Fecha extracto`
- `Concepto extracto`
- `Monto extracto`
- `Fecha contable`
- `Concepto contable`
- `Monto contable`
- `Estado` (por ejemplo: `Conciliado`, `Posible`, `No conciliado`)
- `Observaciones` (información adicional como `% de similitud` o que no se encontró contraparte).

---

### Carpeta de salida `outputs/`

Cada vez que se ejecuta una conciliación exitosa:

- Se genera un archivo Excel con nombre:

  ```text
  conciliacion_YYYYMMDD_HHMMSS.xlsx
  ```

- Se guarda en la carpeta `outputs/` en la raíz del proyecto.
- El backend devuelve ese mismo archivo como descarga al frontend.

Si la carpeta `outputs/` no existe, se crea automáticamente al arrancar el backend, gracias a la configuración en `backend/config.py`.

---

### Errores comunes y manejo

El backend devuelve errores en formato JSON claro, por ejemplo:

- Falta uno de los archivos:
  - `{"detail": "Debe enviar ambos archivos: extractos y contable."}`
- Archivo vacío:
  - `{"detail": "El archivo de extractos está vacío."}`
  - `{"detail": "El archivo contable está vacío."}`
- No se encuentra alguna columna requerida o el Excel está vacío:
  - Mensaje descriptivo indicando el problema de columnas o contenido.
- Error interno inesperado:
  - `{"detail": "Error interno al realizar la conciliación: ..."}`

En el frontend, estos mensajes se muestran en la zona de mensajes bajo el formulario.

---

### Estructura del proyecto

```text
conciliador-contable/
├── backend/
│   ├── main.py
│   ├── conciliador.py
│   ├── normalizador.py
│   ├── schemas.py
│   └── config.py
│
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
│
├── outputs/
│   └── .gitkeep
│
├── requirements.txt
└── README.md
```

Siguiendo los pasos de este README, la aplicación debería funcionar completamente desde la primera ejecución.

