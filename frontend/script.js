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
const bancoExtractosSelect = document.getElementById("banco-extractos");
const extractosHojaField = document.getElementById("extractos-hoja-field");
const extractosHojaSelect = document.getElementById("extractos-hoja-select");
const chequesField = document.getElementById("cheques-diferidos-field");
const paginaChequesSelect = document.getElementById("pagina-cheques-diferidos");
const infoHojasExtracto = document.getElementById("info-hojas-extracto");
const contableHojaField = document.getElementById("contable-hoja-field");
const contableHojaSelect = document.getElementById("contable-hoja-select");
const modoComparacionSelect = document.getElementById("modo-comparacion");
const limpiarBtn = document.getElementById("limpiar-btn");

let totalHojasExtracto = null;
let nombresHojasExtracto = [];
let totalHojasContable = null;
let nombresHojasContable = [];

const TEMA_KEY = "conciliador-tema";

// Cargar lista de bancos para el selector de extractos
async function cargarBancos() {
  if (!bancoExtractosSelect) return;
  try {
    const response = await fetch(`${API_BASE_URL}/bancos`);
    if (!response.ok) return;
    const data = await response.json();
    const bancos = data.bancos || [];
    bancoExtractosSelect.innerHTML = '<option value="" disabled selected>Seleccionar banco...</option>';
    bancos.forEach((b) => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.nombre;
      bancoExtractosSelect.appendChild(opt);
    });
  } catch (_) {
    // Si el backend no está disponible, dejar solo el placeholder
  }
}
cargarBancos();

function esTemaOscuro() {
  return document.body.classList.contains("dark-theme");
}

function aplicarTema(oscuro) {
  if (oscuro) {
    document.body.classList.add("dark-theme");
    if (temaBtn) temaBtn.setAttribute("aria-checked", "true");
  } else {
    document.body.classList.remove("dark-theme");
    if (temaBtn) temaBtn.setAttribute("aria-checked", "false");
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

if (temaBtn) {
  initTema();
  temaBtn.addEventListener("click", () => aplicarTema(!esTemaOscuro()));
}

function actualizarUploadZone(input, zoneId, filenameId) {
  const zone = document.getElementById(zoneId);
  const filenameSpan = document.getElementById(filenameId);
  if (!zone || !filenameSpan) return;
  const file = input.files && input.files[0];
  if (file) {
    zone.classList.add("has-file");
    filenameSpan.textContent = file.name;
  } else {
    zone.classList.remove("has-file");
    filenameSpan.textContent = "";
  }
}

function setupUploadZone(inputId, zoneId, filenameId) {
  const input = document.getElementById(inputId);
  const zone = document.getElementById(zoneId);
  if (!input || !zone) return;
  input.addEventListener("change", () => {
    actualizarUploadZone(input, zoneId, filenameId);
    const file = input.files && input.files[0];
    if (inputId === "extractos_file") {
      manejarCambioExtractosFile(file);
    } else if (inputId === "contable_file") {
      manejarCambioContableFile(file);
    }
  });
  ["dragenter", "dragover"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.add("drag-over");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove("drag-over");
    });
  });
  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith(".xlsx")) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      actualizarUploadZone(input, zoneId, filenameId);
    }
  });
}

setupUploadZone("extractos_file", "upload-zone-extractos", "filename-extractos");
setupUploadZone("contable_file", "upload-zone-contable", "filename-contable");

let ultimoExcelFilename = null;

function resetChequesDiferidos() {
  totalHojasExtracto = null;
  nombresHojasExtracto = [];
  if (extractosHojaSelect) {
    extractosHojaSelect.innerHTML =
      '<option value="" disabled selected>Seleccionar hoja de extractos...</option>';
  }
  if (paginaChequesSelect) {
    paginaChequesSelect.innerHTML = '<option value="" selected>Sin cheques diferidos</option>';
  }
  if (extractosHojaField) extractosHojaField.style.display = "none";
  if (chequesField) chequesField.style.display = "none";
  if (infoHojasExtracto) infoHojasExtracto.textContent = "";
}

// Asegurar que el bloque de cheques diferidos esté oculto al cargar la página.
resetChequesDiferidos();

function resetContableHojas() {
  totalHojasContable = null;
  nombresHojasContable = [];
  if (contableHojaSelect) {
    contableHojaSelect.innerHTML =
      '<option value="" disabled selected>Seleccionar hoja contable...</option>';
  }
  if (contableHojaField) contableHojaField.style.display = "none";
}
resetContableHojas();

async function manejarCambioExtractosFile(file) {
  resetChequesDiferidos();
  if (!file) return;
  try {
    const formData = new FormData();
    formData.append("extractos_file", file);
    const response = await fetch(`${API_BASE_URL}/info_extracto`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) return;
    const data = await response.json();
    const total = typeof data.total_hojas === "number" ? data.total_hojas : 0;
    const hojas = Array.isArray(data.hojas) ? data.hojas : [];
    totalHojasExtracto = total;
    nombresHojasExtracto = hojas.map((h) =>
      h && h.nombre ? h.nombre : `Hoja ${h.indice || ""}`
    );

    if (totalHojasExtracto > 0) {
      if (extractosHojaField) extractosHojaField.style.display = "flex";
      if (chequesField) chequesField.style.display = "flex";

      if (extractosHojaSelect) {
        extractosHojaSelect.innerHTML =
          '<option value="" disabled selected>Seleccionar hoja de extractos...</option>';
        nombresHojasExtracto.forEach((nombre, idx) => {
          const opt = document.createElement("option");
          opt.value = String(idx + 1);
          opt.textContent = `${idx + 1} - ${nombre}`;
          extractosHojaSelect.appendChild(opt);
        });
      }

      if (paginaChequesSelect) {
        paginaChequesSelect.innerHTML =
          '<option value="" selected>Sin cheques diferidos</option>';
        nombresHojasExtracto.forEach((nombre, idx) => {
          const opt = document.createElement("option");
          opt.value = String(idx + 1);
          opt.textContent = `${idx + 1} - ${nombre}`;
          paginaChequesSelect.appendChild(opt);
        });
      }

      if (infoHojasExtracto) {
        infoHojasExtracto.textContent =
          totalHojasExtracto === 1
            ? "El archivo de extractos tiene 1 hoja."
            : `El archivo de extractos tiene ${totalHojasExtracto} hojas.`;
      }
    }
  } catch (_) {
    // Si falla, se deja el check oculto y no se interrumpe el flujo principal.
  }
}

async function manejarCambioContableFile(file) {
  resetContableHojas();
  if (!file) return;
  try {
    const formData = new FormData();
    formData.append("contable_file", file);
    const response = await fetch(`${API_BASE_URL}/info_contable`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) return;
    const data = await response.json();
    const total = typeof data.total_hojas === "number" ? data.total_hojas : 0;
    const hojas = Array.isArray(data.hojas) ? data.hojas : [];
    totalHojasContable = total;
    nombresHojasContable = hojas.map((h) =>
      h && h.nombre ? h.nombre : `Hoja ${h.indice || ""}`
    );

    if (totalHojasContable > 0 && contableHojaField && contableHojaSelect) {
      contableHojaField.style.display = "flex";
      contableHojaSelect.innerHTML =
        '<option value="" disabled selected>Seleccionar hoja contable...</option>';
      nombresHojasContable.forEach((nombre, idx) => {
        const opt = document.createElement("option");
        opt.value = String(idx + 1);
        opt.textContent = `${idx + 1} - ${nombre}`;
        contableHojaSelect.appendChild(opt);
      });
    }
  } catch (_) {
    // si falla, no mostramos el combo pero no interrumpimos el flujo principal
  }
}

function limpiarMensajes() {
  mensajesContainer.innerHTML = "";
}

/** Limpia los campos del formulario (banco, archivos) para poder cargar nuevos. */
function limpiarFormulario() {
  const extractosFileInput = document.getElementById("extractos_file");
  const contableFileInput = document.getElementById("contable_file");
  if (extractosFileInput) {
    extractosFileInput.value = "";
    actualizarUploadZone(extractosFileInput, "upload-zone-extractos", "filename-extractos");
  }
  if (contableFileInput) {
    contableFileInput.value = "";
    actualizarUploadZone(contableFileInput, "upload-zone-contable", "filename-contable");
  }
  if (bancoExtractosSelect) {
    bancoExtractosSelect.value = "";
  }
  resetChequesDiferidos();
  resetContableHojas();
  if (modoComparacionSelect) {
    modoComparacionSelect.value = "fecha_monto";
  }
  ultimoExcelFilename = null;
  if (descargarExcelBtn) {
    descargarExcelBtn.style.display = "none";
  }
  resultadoContenedor.hidden = true;
  limpiarMensajes();
}

if (limpiarBtn) {
  limpiarBtn.addEventListener("click", () => {
    limpiarFormulario();
  });
}

function agregarMensaje(texto, tipo = "info") {
  const div = document.createElement("div");
  div.className = `mensaje ${tipo}`;
  div.textContent = texto;
  mensajesContainer.appendChild(div);
}

function formatearMonto(num) {
  if (num === undefined || num === null || Number.isNaN(Number(num))) return "—";
  return new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(num));
}

function formatearFecha(str) {
  if (str === undefined || str === null) return "—";
  str = String(str).trim();
  if (str === "") return "—";
  if (str.includes("/")) return str;
  const partes = str.split("-");
  const a = partes[0];
  const m = partes[1];
  const d = partes[2];
  if (partes.length >= 3 && a && m && d) return `${d}/${m}/${a}`;
  return str;
}

function safeStr(val) {
  if (val === undefined || val === null) return "";
  return String(val).trim();
}

function renderizarMovimiento(mov) {
  if (!mov || typeof mov !== "object") return document.createElement("li");
  const fecha = formatearFecha(mov.fecha);
  const monto = formatearMonto(mov.monto);
  const desc = escapeHtml(safeStr(mov.descripcion));
  const li = document.createElement("li");
  li.className = "movimiento-item";
  const fechaSafe = (fecha === "undefined" || fecha == null) ? "—" : fecha;
  const montoSafe = (monto === "undefined" || monto == null) ? "—" : monto;
  const descSafe = (desc === "undefined" || desc == null) ? "" : desc;
  li.innerHTML = `
    <span class="mov-fecha">${fechaSafe}</span>
    <span class="mov-monto">$${montoSafe}</span>
    <span class="mov-descripcion">${descSafe}</span>
  `;
  return li;
}

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function mostrarResultado(data) {
  const solo_en_extractos = Array.isArray(data.solo_en_extractos) ? data.solo_en_extractos : [];
  const solo_en_contable = Array.isArray(data.solo_en_contable) ? data.solo_en_contable : [];
  const resumen = data.resumen || {};
  const modo = data.modo_comparacion || "fecha_monto";
  let descripcionModo = "según el modo seleccionado";
  if (modo === "fecha_monto") {
    descripcionModo = "con fecha y monto iguales";
  }

  resumenTexto.textContent =
    `${resumen.coincidencias ?? 0} coincidencias (${descripcionModo}). ` +
    `${resumen.diferentes_extractos ?? 0} solo en extractos. ` +
    `${resumen.diferentes_contable ?? 0} solo en contable.`;

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
  const bancoVal = bancoExtractosSelect && bancoExtractosSelect.value;
  const extractosHojaVal = extractosHojaSelect && extractosHojaSelect.value;
  const contableHojaVal = contableHojaSelect && contableHojaSelect.value;
  const paginaChequesVal = paginaChequesSelect && paginaChequesSelect.value;
  const modoVal = modoComparacionSelect && modoComparacionSelect.value;

  if (!bancoVal) {
    agregarMensaje("Debe seleccionar el banco del archivo de extractos.", "error");
    return;
  }
  if (!extractosFileInput.files[0] || !contableFileInput.files[0]) {
    agregarMensaje("Debe seleccionar ambos archivos antes de comparar.", "error");
    return;
  }
  if (!extractosHojaVal) {
    agregarMensaje("Debe seleccionar la hoja de extractos a analizar.", "error");
    return;
  }
  if (!contableHojaVal) {
    agregarMensaje("Debe seleccionar la hoja contable a analizar.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("banco_extractos", bancoVal);
  formData.append("extractos_file", extractosFileInput.files[0]);
  formData.append("contable_file", contableFileInput.files[0]);
  formData.append("extractos_hoja_index", extractosHojaVal);
  formData.append("contable_hoja_index", contableHojaVal);
  formData.append("modo_comparacion", modoVal || "fecha_monto");
  if (paginaChequesVal && paginaChequesVal !== "0" && paginaChequesVal !== "") {
    formData.append("cheques_diferidos_hoja_index", paginaChequesVal);
  }

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

