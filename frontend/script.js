// Lógica de frontend para interactuar con el backend FastAPI.
// - Captura los archivos seleccionados.
// - Envía una petición POST /conciliar con multipart/form-data.
// - Muestra los movimientos que difieren entre ambos Excels.

const API_BASE_URL = "http://localhost:8000";

const form = document.getElementById("conciliacion-form");
const mensajesContainer = document.getElementById("mensajes");
const conciliarBtn = document.getElementById("conciliar-btn");
const resultadoContenedor = document.getElementById("resultado-contenedor");
const resumenTexto = document.getElementById("resumen-texto");
const listaGastos = document.getElementById("lista-gastos");
const listaContable = document.getElementById("lista-contable");
const soloGastosDiv = document.getElementById("solo-gastos");
const soloContableDiv = document.getElementById("solo-contable");

function limpiarMensajes() {
  mensajesContainer.innerHTML = "";
}

function agregarMensaje(texto, tipo = "info") {
  const div = document.createElement("div");
  div.className = `mensaje ${tipo}`;
  div.textContent = texto;
  mensajesContainer.appendChild(div);
}

function formatearMonto(num) {
  return new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

function formatearFecha(str) {
  if (!str) return "—";
  const [a, m, d] = str.split("-");
  return `${d}/${m}/${a}`;
}

function renderizarMovimiento(mov) {
  const li = document.createElement("li");
  li.className = "movimiento-item";
  li.innerHTML = `
    <span class="mov-fecha">${formatearFecha(mov.fecha)}</span>
    <span class="mov-monto">$${formatearMonto(mov.monto)}</span>
    <span class="mov-descripcion">${escapeHtml(mov.descripcion || "")}</span>
  `;
  return li;
}

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function mostrarResultado(data) {
  const { solo_en_gastos, solo_en_contable, resumen } = data;

  resumenTexto.textContent = `${resumen.coincidencias} coincidencias (fecha + monto iguales). ` +
    `${resumen.diferentes_gastos} solo en gastos. ${resumen.diferentes_contable} solo en contable.`;

  listaGastos.innerHTML = "";
  listaContable.innerHTML = "";

  if (solo_en_gastos.length > 0) {
    soloGastosDiv.hidden = false;
    solo_en_gastos.forEach((mov) => listaGastos.appendChild(renderizarMovimiento(mov)));
  } else {
    soloGastosDiv.hidden = true;
  }

  if (solo_en_contable.length > 0) {
    soloContableDiv.hidden = false;
    solo_en_contable.forEach((mov) => listaContable.appendChild(renderizarMovimiento(mov)));
  } else {
    soloContableDiv.hidden = true;
  }

  resultadoContenedor.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  limpiarMensajes();
  resultadoContenedor.hidden = true;

  const gastosFileInput = document.getElementById("gastos_file");
  const contableFileInput = document.getElementById("contable_file");

  if (!gastosFileInput.files[0] || !contableFileInput.files[0]) {
    agregarMensaje("Debe seleccionar ambos archivos antes de comparar.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("gastos_file", gastosFileInput.files[0]);
  formData.append("contable_file", contableFileInput.files[0]);

  conciliarBtn.disabled = true;
  agregarMensaje("Comparando archivos, por favor espere...", "info");

  try {
    const response = await fetch(`${API_BASE_URL}/conciliar`, {
      method: "POST",
      body: formData,
    });

    const contentType = response.headers.get("content-type") || "";
    if (!response.ok) {
      if (contentType.includes("application/json")) {
        const data = await response.json();
        limpiarMensajes();
        agregarMensaje(data.detail || "Error desconocido en el backend.", "error");
      } else {
        limpiarMensajes();
        agregarMensaje("Error inesperado al procesar la comparación.", "error");
      }
      return;
    }

    const data = await response.json();
    limpiarMensajes();
    agregarMensaje("Comparación completada.", "success");
    mostrarResultado(data);
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

