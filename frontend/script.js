// Lógica de frontend para interactuar con el backend FastAPI.
// - Captura los archivos seleccionados.
// - Envía una petición POST /conciliar con multipart/form-data.
// - Muestra estados de carga y errores.
// - Descarga automáticamente el Excel resultado.

const API_BASE_URL = "http://localhost:8000";

const form = document.getElementById("conciliacion-form");
const mensajesContainer = document.getElementById("mensajes");
const descargarBtn = document.getElementById("descargar-btn");
const conciliarBtn = document.getElementById("conciliar-btn");

let ultimoBlobUrl = null;
let ultimoNombreArchivo = null;

function limpiarMensajes() {
  mensajesContainer.innerHTML = "";
}

function agregarMensaje(texto, tipo = "info") {
  const div = document.createElement("div");
  div.className = `mensaje ${tipo}`;
  div.textContent = texto;
  mensajesContainer.appendChild(div);
}

async function manejarDescargaManual() {
  // Descarga manual del último resultado generado.
  if (!ultimoBlobUrl || !ultimoNombreArchivo) return;

  const a = document.createElement("a");
  a.href = ultimoBlobUrl;
  a.download = ultimoNombreArchivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

descargarBtn.addEventListener("click", manejarDescargaManual);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  limpiarMensajes();

  const gastosFileInput = document.getElementById("gastos_file");
  const contableFileInput = document.getElementById("contable_file");

  if (!gastosFileInput.files[0] || !contableFileInput.files[0]) {
    agregarMensaje("Debe seleccionar ambos archivos antes de conciliar.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("gastos_file", gastosFileInput.files[0]);
  formData.append("contable_file", contableFileInput.files[0]);

  conciliarBtn.disabled = true;
  descargarBtn.disabled = true;
  agregarMensaje("Procesando conciliación, por favor espere...", "info");

  try {
    const response = await fetch(`${API_BASE_URL}/conciliar`, {
      method: "POST",
      body: formData,
    });

    // Comprobamos si el backend devolvió un error JSON
    const contentType = response.headers.get("content-type") || "";
    if (!response.ok) {
      if (contentType.includes("application/json")) {
        const data = await response.json();
        limpiarMensajes();
        agregarMensaje(data.detail || "Error desconocido en el backend.", "error");
      } else {
        limpiarMensajes();
        agregarMensaje("Error inesperado al procesar la conciliación.", "error");
      }
      return;
    }

    // Éxito: esperamos un archivo Excel (blob)
    const blob = await response.blob();
    if (ultimoBlobUrl) {
      URL.revokeObjectURL(ultimoBlobUrl);
    }
    ultimoBlobUrl = URL.createObjectURL(blob);

    // Nombre de archivo sugerido por el backend
    const disposition = response.headers.get("content-disposition") || "";
    const matchFilename = disposition.match(/filename="?([^"]+)"?/i);
    ultimoNombreArchivo = matchFilename ? matchFilename[1] : "conciliacion.xlsx";

    limpiarMensajes();
    agregarMensaje("Conciliación generada correctamente.", "success");
    descargarBtn.disabled = false;

    // Descarga automática del archivo
    manejarDescargaManual();
  } catch (error) {
    console.error(error);
    limpiarMensajes();
    agregarMensaje(
      "No fue posible conectar con el servidor. Verifique que el backend esté ejecutándose.",
      "error"
    );
  } finally {
    conciliarBtn.disabled = false;
  }
});

