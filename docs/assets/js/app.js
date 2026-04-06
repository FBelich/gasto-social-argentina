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
    const d = await fetchJSON(`data/${key}.json`);
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

  // KPIs
  renderKPIs("anses-kpis", meta, ts);

  // ── Evolución histórica ──────────────────────────────────────────────────
  // Actualizar badge del bubble nav
  const bkpi = document.getElementById("bkpi-anses");
  if (bkpi && meta.total_ultimo_anio) {
    bkpi.textContent = fmtNum(meta.total_ultimo_anio) + " $";
  }

  // Gráfico de línea: total histórico
  renderLineChart("anses-line-total", ts, color);

  // Gráfico de barras apiladas: por clasificador
  if (ts.datasets && ts.datasets.length > 0) {
    renderStackedBar("anses-stacked", ts, PALETTE_ANSES);
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

  // Generar una card por cada clasificador con datos
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

  // Renderizar cada gráfico de barras horizontales
  comp.cards.forEach((card, i) => {
    renderHBar(`hbar-${i}`, card, color);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Navegación por burbujas
// ─────────────────────────────────────────────────────────────────────────────

async function activarSeccion(key) {
  // Actualizar estado visual de los botones
  document.querySelectorAll(".bubble").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".cpanel").forEach(p => p.classList.remove("active"));

  const bubble = document.querySelector(`.bubble[data-section="${key}"]`);
  const panel  = document.getElementById(`panel-${key}`);

  if (bubble) bubble.classList.add("active");
  if (panel)  panel.classList.add("active");

  // Cargar datos si no están cargados
  const overlay = document.getElementById("loverlay");
  if (!DATA[key]) {
    if (overlay) overlay.classList.remove("hidden");
    const d = await loadSection(key);
    if (overlay) overlay.classList.add("hidden");
    if (!d) {
      showError(`No se pudieron cargar los datos de la sección "${key}". Ejecutá el pipeline de Python primero.`);
      return;
    }
  }

  // Renderizar según la sección
  if (key === "anses") renderAnses(DATA[key]);
  // Futuras secciones: else if (key === "educacion") renderEducacion(DATA[key]);
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

  // Inicializar navegación
  document.querySelectorAll(".bubble").forEach(btn => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.section;
      if (key) activarSeccion(key);
    });
  });

  // Cargar index.json para saber qué secciones hay
  try {
    const idx = await fetchJSON("data/index.json");
    SECTIONS = idx.secciones || [];
    // Actualizar fecha en el header
    const fechaEl = document.getElementById("headerSub");
    if (fechaEl && SECTIONS.length > 0) {
      const last = SECTIONS[0].ultima_actualizacion || "";
      fechaEl.textContent = `Actualizado: ${last}`;
    }
  } catch (e) {
    console.warn("No se pudo cargar index.json:", e.message);
  }

  // Activar primera sección por defecto (ANSES)
  if (overlay) overlay.classList.remove("hidden");
  await activarSeccion("anses");
  if (overlay) overlay.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", init);
