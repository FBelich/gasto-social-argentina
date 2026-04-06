/* ============================================================
   charts.js  –  Funciones de renderizado con ECharts
   Todas las funciones reciben (elementId, data, opciones)
   ============================================================ */

"use strict";

// ── Paleta de colores ──────────────────────────────────────────────────────
const PALETTE_ANSES = [
  "#007AFF","#5856D6","#AF52DE","#FF2D55","#FF9F0A",
  "#34C759","#00C7BE","#32ADE6","#64D2FF","#BF5AF2"
];

// ── Formateo de números ────────────────────────────────────────────────────
function fmtNum(v) {
  if (v === null || v === undefined || isNaN(v)) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e12) return (v / 1e12).toLocaleString("es-AR", { maximumFractionDigits: 1 }) + " B";
  if (abs >= 1e9)  return (v / 1e9 ).toLocaleString("es-AR", { maximumFractionDigits: 1 }) + " MM";
  if (abs >= 1e6)  return (v / 1e6 ).toLocaleString("es-AR", { maximumFractionDigits: 1 }) + " M";
  return Math.round(v).toLocaleString("es-AR");
}

function fmtFull(v) {
  if (v === null || v === undefined || isNaN(v)) return "—";
  return Math.round(v).toLocaleString("es-AR");
}

// ── Opciones base compartidas ──────────────────────────────────────────────
function baseGrid() {
  return { top: 20, right: 20, bottom: 56, left: 64 };
}

function baseTooltip(formatter) {
  return {
    trigger: "axis",
    backgroundColor: "rgba(255,255,255,.97)",
    borderColor: "rgba(0,0,0,.07)",
    borderWidth: 1,
    textStyle: { fontFamily: "'DM Sans', sans-serif", fontSize: 12, color: "#1c1c1e" },
    padding: [10, 14],
    extraCssText: "border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.10);",
    formatter: formatter || null,
  };
}

// ── Línea de evolución histórica (serie única) ─────────────────────────────
function renderLineChart(elementId, data, accentColor) {
  const el = document.getElementById(elementId);
  if (!el || !data || !data.labels) return;

  const chart = echarts.init(el, null, { renderer: "canvas" });
  const color = accentColor || PALETTE_ANSES[0];

  chart.setOption({
    animation: true,
    animationDuration: 800,
    grid: baseGrid(),
    tooltip: baseTooltip(function(params) {
      const p = params[0];
      return `<div style="font-weight:600;margin-bottom:4px">${p.axisValue}</div>
              <div style="display:flex;align-items:center;gap:6px">
                <span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block"></span>
                ${fmtFull(p.value)} $
              </div>`;
    }),
    xAxis: {
      type: "category",
      data: data.labels,
      axisLine:  { lineStyle: { color: "rgba(0,0,0,.1)" } },
      axisTick:  { show: false },
      axisLabel: { fontFamily: "'DM Sans',sans-serif", fontSize: 11, color: "#6e6e73" },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(0,0,0,.05)" } },
      axisLabel: {
        fontFamily: "'DM Mono','SF Mono',monospace",
        fontSize: 10, color: "#6e6e73",
        formatter: v => fmtNum(v),
      },
    },
    series: [{
      type: "line",
      data: data.total,
      smooth: 0.3,
      lineStyle: { color, width: 2.5 },
      itemStyle: { color },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color + "40" },
          { offset: 1, color: color + "00" },
        ]),
      },
      symbol: "circle", symbolSize: 4,
      emphasis: { scale: true, itemStyle: { symbolSize: 8 } },
    }],
  });

  window.addEventListener("resize", () => chart.resize());
  return chart;
}

// ── Barras apiladas (series múltiples) ────────────────────────────────────
function renderStackedBar(elementId, data, accentColors) {
  const el = document.getElementById(elementId);
  if (!el || !data || !data.labels || !data.datasets) return;

  const chart  = echarts.init(el, null, { renderer: "canvas" });
  const colors = accentColors || PALETTE_ANSES;

  const series = data.datasets.map((ds, i) => ({
    name:  ds.label,
    type:  "bar",
    stack: "total",
    data:  ds.data,
    itemStyle: { color: colors[i % colors.length], borderRadius: i === data.datasets.length - 1 ? [4,4,0,0] : 0 },
    emphasis: { focus: "series" },
    label: { show: false },
  }));

  chart.setOption({
    animation: true,
    animationDuration: 900,
    color: colors,
    grid: { ...baseGrid(), bottom: 70 },
    legend: {
      bottom: 0, type: "scroll",
      textStyle: { fontFamily: "'DM Sans',sans-serif", fontSize: 11, color: "#6e6e73" },
      pageTextStyle: { color: "#6e6e73" },
    },
    tooltip: {
      trigger: "axis", axisPointer: { type: "shadow" },
      backgroundColor: "rgba(255,255,255,.97)",
      borderColor: "rgba(0,0,0,.07)", borderWidth: 1,
      textStyle: { fontFamily: "'DM Sans',sans-serif", fontSize: 12, color: "#1c1c1e" },
      padding: [10,14],
      extraCssText: "border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.10);",
      formatter(params) {
        let html = `<div style="font-weight:600;margin-bottom:6px">${params[0].axisValue}</div>`;
        let total = 0;
        params.forEach(p => {
          if (p.value == null) return;
          total += p.value;
          html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">
            <span style="width:8px;height:8px;border-radius:50%;background:${p.color};display:inline-block;flex-shrink:0"></span>
            <span style="flex:1;font-size:11px">${p.seriesName}</span>
            <span style="font-family:'DM Mono',monospace;font-size:11px">${fmtFull(p.value)}</span>
          </div>`;
        });
        html += `<div style="border-top:1px solid rgba(0,0,0,.07);margin-top:6px;padding-top:6px;font-weight:600;display:flex;justify-content:space-between">
          <span>Total</span><span style="font-family:'DM Mono',monospace">${fmtFull(total)}</span>
        </div>`;
        return html;
      },
    },
    xAxis: {
      type: "category", data: data.labels,
      axisLine:  { lineStyle: { color: "rgba(0,0,0,.1)" } },
      axisTick:  { show: false },
      axisLabel: { fontFamily: "'DM Sans',sans-serif", fontSize: 11, color: "#6e6e73" },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(0,0,0,.05)" } },
      axisLabel: {
        fontFamily: "'DM Mono','SF Mono',monospace",
        fontSize: 10, color: "#6e6e73",
        formatter: v => fmtNum(v),
      },
    },
    series,
  });

  window.addEventListener("resize", () => chart.resize());
  return chart;
}

// ── Barras horizontales (composición) ─────────────────────────────────────
function renderHBar(elementId, data, accentColor) {
  const el = document.getElementById(elementId);
  if (!el || !data || !data.labels) return;

  const chart = echarts.init(el, null, { renderer: "canvas" });
  const color = accentColor || PALETTE_ANSES[0];

  // Calcular altura dinámica según cantidad de categorías
  const n = data.labels.length;
  el.style.height = Math.max(200, n * 36 + 40) + "px";
  chart.resize();

  const colorArray = data.labels.map((_, i) =>
    PALETTE_ANSES[i % PALETTE_ANSES.length]
  );

  chart.setOption({
    animation: true,
    animationDuration: 700,
    grid: { top: 10, right: 120, bottom: 20, left: 10, containLabel: true },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(255,255,255,.97)",
      borderColor: "rgba(0,0,0,.07)", borderWidth: 1,
      textStyle: { fontFamily: "'DM Sans',sans-serif", fontSize: 12, color: "#1c1c1e" },
      padding: [10,14],
      extraCssText: "border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.10);",
      formatter(p) {
        const pct = data.total ? ((p.value / data.total) * 100).toFixed(1) : "—";
        return `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>
                <div style="font-family:'DM Mono',monospace">${fmtFull(p.value)} $</div>
                <div style="color:#6e6e73;font-size:11px">${pct}% del total</div>`;
      },
    },
    xAxis: { type: "value", show: false },
    yAxis: {
      type: "category",
      data: [...data.labels].reverse(),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: {
        fontFamily: "'DM Sans',sans-serif", fontSize: 11, color: "#1c1c1e",
        width: 180, overflow: "truncate",
      },
    },
    series: [{
      type: "bar", barMaxWidth: 22,
      data: [...data.values].reverse().map((v, i) => ({
        value: v,
        itemStyle: { color: PALETTE_ANSES[(data.labels.length - 1 - i) % PALETTE_ANSES.length], borderRadius: [0,6,6,0] },
      })),
      label: {
        show: true, position: "right",
        fontFamily: "'DM Mono','SF Mono',monospace", fontSize: 10, color: "#6e6e73",
        formatter: p => fmtNum(p.value),
      },
      emphasis: { focus: "self" },
    }],
  });

  window.addEventListener("resize", () => chart.resize());
  return chart;
}

// ── Donut ─────────────────────────────────────────────────────────────────
function renderDonut(elementId, data, accentColor) {
  const el = document.getElementById(elementId);
  if (!el || !data || !data.labels) return;

  const chart = echarts.init(el, null, { renderer: "canvas" });

  const seriesData = data.labels.map((label, i) => ({
    name:  label,
    value: data.values[i],
    itemStyle: { color: PALETTE_ANSES[i % PALETTE_ANSES.length] },
  }));

  chart.setOption({
    animation: true,
    animationDuration: 700,
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(255,255,255,.97)",
      borderColor: "rgba(0,0,0,.07)", borderWidth: 1,
      textStyle: { fontFamily: "'DM Sans',sans-serif", fontSize: 12 },
      padding: [10,14],
      extraCssText: "border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.10);",
      formatter(p) {
        return `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>
                <div style="font-family:'DM Mono',monospace">${fmtFull(p.value)} $</div>
                <div style="color:#6e6e73;font-size:11px">${p.percent}%</div>`;
      },
    },
    legend: { show: false },
    series: [{
      type: "pie", radius: ["50%", "75%"],
      center: ["50%", "50%"],
      data: seriesData,
      label: { show: false },
      emphasis: { scale: true, scaleSize: 6 },
      itemStyle: { borderWidth: 2, borderColor: "#fff" },
    }],
  });

  window.addEventListener("resize", () => chart.resize());
  return chart;
}
