/* ============================================================
   app.js  –  Lógica principal del dashboard
   Carga JSONs → renderiza secciones → gestiona navegación
   ============================================================ */

"use strict";

// ─────────────────────────────────────────────────────────────────────────────
// Estado global
// ─────────────────────────────────────────────────────────────────────────────
const DATA = {};     // { anses: { meta, timeseries, composition }, ... }
let SECTIONS = [];   // Lista de secciones del index.json

// ─────────────────────────────────────────────────────────────────────────────
// Carga de datos
// ─────────────────────────────────────────────────────────────────────────────

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status} al cargar ${path}`);
  return res.json();
}

async function loadSection(key) {
  if (DATA[key]) return DATA[key];
  try {
    // Le agregamos un timestamp falso al final para romper la caché del JSON
    const timestamp = new Date().getTime();
    const d = await fetchJSON(`data/${key}.json?t=${timestamp}`);
    
    DATA[key] = d;
    return d;
  } catch (e) {
    console.error(`Error cargando sección ${key}:`, e);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI cards
// ─────────────────────────────────────────────────────────────────────────────

function calcVariacion(ts) {
  const totals = ts.total;
  if (!totals || totals.length < 2) return null;
  const prev = totals[totals.length - 2];
  const last = totals[totals.length - 1];
  if (!prev) return null;
  return ((last - prev) / prev) * 100;
}

function renderKPIs(containerId, meta, ts) {
  const el = document.getElementById(containerId);
  if (!el) return;

  const color = meta.color;
  const varPct = calcVariacion(ts);
  const varClass = varPct === null ? "neutral" : varPct >= 0 ? "up" : "down";
  const varIcon  = varPct === null ? "—" : varPct >= 0 ? "▲" : "▼";
  const varStr   = varPct !== null ? `${varIcon} ${Math.abs(varPct).toFixed(1)}% vs año anterior` : "—";

  const totalHist = fmtNum(meta.total_historico);
  const totalUlt  = fmtNum(meta.total_ultimo_anio);
  const periodo   = ts.labels && ts.labels.length > 0
    ? `${ts.labels[0]}–${ts.labels[ts.labels.length - 1]}`
    : "—";

  el.innerHTML = `
    <div class="kcard">
      <div class="klbl">Crédito devengado · ${meta.anio_fin}</div>
      <div class="kval" style="color:${color}">${totalUlt}<span class="kunit">$</span></div>
      <div class="kdelta ${varClass}">${varStr}</div>
    </div>
    <div class="kcard">
      <div class="klbl">Total histórico · ${periodo}</div>
      <div class="kval">${totalHist}<span class="kunit">$</span></div>
      <div class="kdelta neutral">Acumulado</div>
    </div>
    <div class="kcard">
      <div class="klbl">Años con datos</div>
      <div class="kval">${ts.labels ? ts.labels.length : "—"}</div>
      <div class="kdelta neutral">${periodo}</div>
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────────────────
// Renderizado de sección ANSES
// ─────────────────────────────────────────────────────────────────────────────

function renderAnses(d) {
  const { meta, timeseries: ts, composition: comp } = d;
  const color = meta.color;

  // Guardar datos globalmente para los botones Anual/Mensual
  DATA["anses"] = d;

  // KPIs: Le ponemos un salvavidas. Si no encuentra "ts.anual", usa "ts" (formato viejo)
  const datosKPI = ts.anual ? ts.anual : ts; 
  renderKPIs("anses-kpis", meta, datosKPI);

  // ── Evolución histórica ──────────────────────────────────────────────────
  const bkpi = document.getElementById("bkpi-anses");
  if (bkpi && meta.total_ultimo_anio) {
    bkpi.textContent = fmtNum(meta.total_ultimo_anio) + " $";
  }

  // Gráfico de línea: Usar ts.anual por defecto
  const serieLinea = ts.anual ? ts.anual : ts;
  renderLineChart("anses-line-total", serieLinea, color);

  // Gráfico de barras apiladas: Usar ts.anual
  if (serieLinea.datasets && serieLinea.datasets.length > 0) {
    renderStackedBar("anses-stacked", serieLinea, PALETTE_ANSES);
  } else {
    const el = document.getElementById("anses-stacked");
    if (el) el.closest(".card").innerHTML = `
      <div class="empty-state">
        <div class="icon">📊</div>
        <p>No hay desagregación disponible para este período.</p>
      </div>`;
  }

  // ── Composición del último año ────────────────────────────────────────────
  const compContainer = document.getElementById("anses-composition");
  if (!compContainer) return;

  if (!comp || !comp.cards || comp.cards.length === 0) {
    compContainer.innerHTML = `
      <div class="empty-state">
        <div class="icon">📋</div>
        <p>No hay datos de composición disponibles para ${meta.anio_fin}.</p>
      </div>`;
    return;
  }

  const cardsHTML = comp.cards.map((card, i) => `
    <div class="card" style="animation-delay:${i * 0.05}s">
      <div class="card-hdr">
        <div>
          <div class="ctitle">${card.titulo}</div>
          <div class="csub">Total: ${fmtFull(card.total)} $  ·  ${comp.anio}</div>
        </div>
        <span class="cpill">${card.labels.length} categorías</span>
      </div>
      <div class="cwrap">
        <div id="hbar-${i}" style="height:200px;width:100%"></div>
      </div>
    </div>
  `).join("");

  compContainer.innerHTML = cardsHTML;

  comp.cards.forEach((card, i) => {
    renderHBar(`hbar-${i}`, card, color);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Controles de Gráficos (Anual / Mensual)
// ─────────────────────────────────────────────────────────────────────────────

window.cambiarFrecuencia = function(frecuencia) {
  if (!DATA["anses"] || !DATA["anses"].timeseries) return;

  const ts = DATA["anses"].timeseries;
  const dataFrecuencia = ts[frecuencia];
  const color = DATA["anses"].meta.color || "#007AFF";

  if (!dataFrecuencia || !dataFrecuencia.labels || dataFrecuencia.labels.length === 0) {
    console.warn("No hay datos para la frecuencia: " + frecuencia);
    return;
  }

  // Destruir la instancia anterior y recrear el gráfico desde cero.
  // Los datos anuales (32 puntos, labels numéricos) y mensuales (~380 puntos,
  // labels "YYYY-MM") tienen escalas incompatibles: un setOption parcial con
  // merge=false deja el gráfico en blanco porque ECharts no limpia el estado
  // interno del eje X al cambiar drásticamente la cantidad de categorías.
  const chartDom = document.getElementById('anses-line-total');
  const existingChart = echarts.getInstanceByDom(chartDom);
  if (existingChart) existingChart.dispose();

  renderLineChart("anses-line-total", dataFrecuencia, color);

  // Cambiar estado visual de los botones
  const btnAnual   = document.getElementById('btn-anual-anses');
  const btnMensual = document.getElementById('btn-mensual-anses');
  if (btnAnual && btnMensual) {
    btnAnual.classList.remove('active');
    btnMensual.classList.remove('active');
    document.getElementById(`btn-${frecuencia}-anses`).classList.add('active');
  }

  // Actualizar el título
  const titulo = document.getElementById('title-line-anses');
  if (titulo) {
    titulo.innerText = frecuencia === 'anual' ? 'Total Anual · ANSES' : 'Total Mensual · ANSES';
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// Navegación por burbujas
// ─────────────────────────────────────────────────────────────────────────────

async function activarSeccion(key) {
  document.querySelectorAll(".bubble").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".cpanel").forEach(p => p.classList.remove("active"));

  const bubble = document.querySelector(`.bubble[data-section="${key}"]`);
  const panel  = document.getElementById(`panel-${key}`);

  if (bubble) bubble.classList.add("active");
  if (panel)  panel.classList.add("active");

  const overlay = document.getElementById("loverlay");
  if (!DATA[key]) {
    if (overlay) overlay.classList.remove("hidden");
    const d = await loadSection(key);
    if (overlay) overlay.classList.add("hidden");
    if (!d) {
      showError(`No se pudieron cargar los datos de la sección "${key}".`);
      return;
    }
  }

  if (key === "anses") renderAnses(DATA[key]);
}

// ─────────────────────────────────────────────────────────────────────────────
// Error handling
// ─────────────────────────────────────────────────────────────────────────────

function showError(msg) {
  const overlay = document.getElementById("loverlay");
  if (overlay) {
    overlay.querySelector(".ltxt").textContent = msg;
    overlay.querySelector(".spinner").style.display = "none";
    overlay.classList.remove("hidden");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Inicialización
// ─────────────────────────────────────────────────────────────────────────────

async function init() {
  const overlay = document.getElementById("loverlay");

  document.querySelectorAll(".bubble").forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.section;
      if (key) activarSeccion(key);
    });
  });

  try {
    const idx = await fetchJSON("data/index.json");
    SECTIONS = idx.secciones || [];
    const fechaEl = document.getElementById("headerSub");
    if (fechaEl && SECTIONS.length > 0) {
      const last = SECTIONS[0].ultima_actualizacion || "";
      fechaEl.textContent = `Actualizado: ${last}`;
    }
  } catch (e) {
    console.warn("No se pudo cargar index.json:", e.message);
  }

  if (overlay) overlay.classList.remove("hidden");
  await activarSeccion("anses");
  if (overlay) overlay.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", init);