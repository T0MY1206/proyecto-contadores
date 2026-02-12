// Lógica de frontend para interactuar con el backend FastAPI.
// - Captura los archivos seleccionados.
// - Envía una petición POST /conciliar con multipart/form-data.
// - Muestra los movimientos que difieren entre ambos Excels.

// En Render (mismo origen) usa la misma URL; en local con archivo abierto usa localhost:8000.
const API_BASE_URL =
  typeof window !== "undefined" &&
  window.location.protocol !== "file:" &&
  window.location.origin !== "null"
    ? window.location.origin
    : "http://localhost:8000";

const form = document.getElementById("conciliacion-form");
const mensajesContainer = document.getElementById("mensajes");
const conciliarBtn = document.getElementById("conciliar-btn");
const resultadoContenedor = document.getElementById("resultado-contenedor");
const resumenTexto = document.getElementById("resumen-texto");
const listaExtractos = document.getElementById("lista-extractos");
const listaContable = document.getElementById("lista-contable");
const soloExtractosDiv = document.getElementById("solo-extractos");
const soloContableDiv = document.getElementById("solo-contable");
const descargarExcelBtn = document.getElementById("descargar-excel-btn");
const temaBtn = document.getElementById("tema-btn");
const temaBtnTexto = document.getElementById("tema-btn-texto");

const TEMA_KEY = "conciliador-tema";

function esTemaOscuro() {
  return document.body.classList.contains("dark-theme");
}

function aplicarTema(oscuro) {
  if (oscuro) {
    document.body.classList.add("dark-theme");
    temaBtnTexto.textContent = "Tema claro";
  } else {
    document.body.classList.remove("dark-theme");
    temaBtnTexto.textContent = "Tema oscuro";
  }
  try {
    localStorage.setItem(TEMA_KEY, oscuro ? "dark" : "light");
  } catch (_) {}
}

function initTema() {
  let preferido = "light";
  try {
    const guardado = localStorage.getItem(TEMA_KEY);
    if (guardado === "dark" || guardado === "light") preferido = guardado;
  } catch (_) {}
  aplicarTema(preferido === "dark");
}

if (temaBtn && temaBtnTexto) {
  initTema();
  temaBtn.addEventListener("click", () => aplicarTema(!esTemaOscuro()));
}

let ultimoExcelFilename = null;

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
  const { solo_en_extractos, solo_en_contable, resumen } = data;

  resumenTexto.textContent = `${resumen.coincidencias} coincidencias (fecha + monto iguales). ` +
    `${resumen.diferentes_extractos} solo en extractos. ${resumen.diferentes_contable} solo en contable.`;

  listaExtractos.innerHTML = "";
  listaContable.innerHTML = "";

  const summaryExtractos = document.getElementById("summary-extractos");
  const summaryContable = document.getElementById("summary-contable");

  if (solo_en_extractos.length > 0) {
    soloExtractosDiv.hidden = false;
    summaryExtractos.textContent = `Solo en archivo de extractos (${solo_en_extractos.length})`;
    solo_en_extractos.forEach((mov) => listaExtractos.appendChild(renderizarMovimiento(mov)));
  } else {
    soloExtractosDiv.hidden = true;
  }

  if (solo_en_contable.length > 0) {
    soloContableDiv.hidden = false;
    summaryContable.textContent = `Solo en archivo contable (${solo_en_contable.length})`;
    solo_en_contable.forEach((mov) => listaContable.appendChild(renderizarMovimiento(mov)));
  } else {
    soloContableDiv.hidden = true;
  }

  resultadoContenedor.hidden = false;
  ultimoExcelFilename = data.excel_filename || null;
  descargarExcelBtn.style.display = ultimoExcelFilename ? "block" : "none";
}

async function descargarExcel() {
  if (!ultimoExcelFilename) return;
  try {
    const response = await fetch(`${API_BASE_URL}/descargar/${ultimoExcelFilename}`);
    if (!response.ok) throw new Error("No se pudo descargar el archivo");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = ultimoExcelFilename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error(err);
    agregarMensaje("Error al descargar el Excel.", "error");
  }
}

descargarExcelBtn.addEventListener("click", descargarExcel);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  limpiarMensajes();
  resultadoContenedor.hidden = true;

  const extractosFileInput = document.getElementById("extractos_file");
  const contableFileInput = document.getElementById("contable_file");

  if (!extractosFileInput.files[0] || !contableFileInput.files[0]) {
    agregarMensaje("Debe seleccionar ambos archivos antes de comparar.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("extractos_file", extractosFileInput.files[0]);
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
    agregarMensaje("Comparación completada. Puede descargar el Excel con el resultado.", "success");
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

