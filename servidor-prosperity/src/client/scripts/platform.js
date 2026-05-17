const page = document.body.dataset.page;
const refreshButton = document.getElementById("refreshButton");
const rangeFilter = document.getElementById("rangeFilter");
const lastRefresh = document.getElementById("lastRefresh");
const nextRefresh = document.getElementById("nextRefresh");
const refreshStatus = document.getElementById("refreshStatus");
const missing = '<span class="data-missing">no disponible</span>';
const dashboardRefreshSeconds = 30;
let nextRefreshAt = Date.now() + dashboardRefreshSeconds * 1000;
let isLoading = false;
let lastSummary = null;
let autoRefreshTimer = null;
let dashboardClockTimer = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function value(value) {
  if (value === null || value === undefined || value === "") {
    return missing;
  }
  return escapeHtml(value);
}

function numberValue(value, digits = 2) {
  if (value === null || value === undefined || value === "") {
    return missing;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(digits) : missing;
}

function formatDate(raw) {
  if (!raw) {
    return "no disponible";
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return String(raw);
  }
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function formatTime(raw) {
  if (!raw) {
    return "no disponible";
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return "no disponible";
  }
  return new Intl.DateTimeFormat("es-CO", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(date);
}

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return `${String(hours).padStart(2, "0")}h ${String(minutes).padStart(2, "0")}m ${String(remainder).padStart(2, "0")}s`;
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(Number(seconds))) {
    return "no disponible";
  }
  return formatDuration(Number(seconds));
}

function badgeClass(status) {
  const key = String(status || "").toLowerCase();
  if (["ok", "open", "valid", "connected", "recibiendo", "operativo", "sent", "disponible"].includes(key)) {
    return "badge-ok";
  }
  if (["hold", "warning", "unknown", "closed", "sin_datos", "sin_archivos"].includes(key)) {
    return "badge-warning";
  }
  if (["error", "invalid", "not_available", "no_disponible"].includes(key)) {
    return "badge-danger";
  }
  return "badge-neutral";
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} respondio ${response.status}`);
  }
  return response.json();
}

function setActiveNav() {
  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.classList.toggle("is-active", link.dataset.nav === page);
  });
}

function statusCard(label, rawValue, detail, status = "neutral") {
  return `
    <article class="status-card status-${escapeHtml(status)}">
      <span class="stats-label">${escapeHtml(label)}</span>
      <strong>${rawValue}</strong>
      <p class="muted">${detail}</p>
    </article>
  `;
}

function sourceBadge(label, status) {
  const normalized = status === "disponible" ? "disponible" : "no disponible";
  return `
    <div class="quality-source">
      <span>${escapeHtml(label)}</span>
      <b class="badge ${badgeClass(status)}">${escapeHtml(normalized)}</b>
    </div>
  `;
}

function renderSparkline(points, label) {
  if (!points?.length) {
    return `<article class="chart-card"><span class="stats-label">${escapeHtml(label)}</span><p class="muted">no disponible</p></article>`;
  }

  const values = points.map((point) => Number(point.value)).filter(Number.isFinite);
  if (!values.length) {
    return `<article class="chart-card"><span class="stats-label">${escapeHtml(label)}</span><p class="muted">no disponible</p></article>`;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = values.length > 1 ? 100 / (values.length - 1) : 100;
  const polyline = values
    .map((item, index) => `${(index * step).toFixed(2)},${(42 - ((item - min) / range) * 34).toFixed(2)}`)
    .join(" ");

  return `
    <article class="chart-card">
      <span class="stats-label">${escapeHtml(label)}</span>
      <svg class="mini-chart" viewBox="0 0 100 48" role="img" aria-label="${escapeHtml(label)}">
        <polyline points="${polyline}" fill="none" stroke="currentColor" stroke-width="2" />
      </svg>
      <p class="muted">Ultimo valor: ${numberValue(values.at(-1))}</p>
    </article>
  `;
}

function renderBars(points, label) {
  if (!points?.length) {
    return `<article class="chart-card"><span class="stats-label">${escapeHtml(label)}</span><p class="muted">datos insuficientes</p></article>`;
  }

  const max = Math.max(...points.map((point) => Number(point.value) || 0), 1);
  return `
    <article class="chart-card">
      <span class="stats-label">${escapeHtml(label)}</span>
      <div class="metric-bars">
        ${points
          .map((point) => {
            const count = Number(point.value) || 0;
            const width = Math.max(6, (count / max) * 100);
            return `
              <div class="metric-bar-row">
                <span>${escapeHtml(point.label)}</span>
                <b style="width:${width}%">${count}</b>
              </div>
            `;
          })
          .join("")}
      </div>
    </article>
  `;
}

function renderWinLossChart(winLoss) {
  if (!winLoss?.available) {
    return `<article class="chart-card"><span class="stats-label">Ganadoras vs perdedoras</span><p class="muted">no disponible: falta fuente con profit real</p></article>`;
  }

  return renderBars(
    [
      { label: "Win", value: winLoss.winners ?? 0 },
      { label: "Loss", value: winLoss.losers ?? 0 },
      { label: "BE", value: winLoss.breakeven ?? 0 },
      { label: "Unknown", value: winLoss.unknown_profit ?? 0 },
    ],
    "Ganadoras vs perdedoras",
  );
}

function compactList(title, items, href, mapper) {
  return `
    <article class="recent-card">
      <div class="recent-card-head">
        <h4>${escapeHtml(title)}</h4>
        <a href="${href}">Ver mas</a>
      </div>
      ${
        items.length
          ? items.map(mapper).join("")
          : '<p class="muted">no disponible</p>'
      }
    </article>
  `;
}

function renderDataQuality(summary) {
  const quality = summary.data_quality || {};
  const warning = quality.incomplete_metrics
    ? `<p class="quality-warning">Advertencia: ${escapeHtml(quality.incomplete_metrics_reason || "metricas incompletas por falta de fuente confiable.")}</p>`
    : "";

  document.getElementById("dataQualityPanel").innerHTML = `
    <article class="quality-card">
      ${sourceBadge("Bot A", quality.bot_a)}
      ${sourceBadge("MAGI decisions", quality.magi_decisions)}
      ${sourceBadge("Bot B", quality.bot_b)}
      ${sourceBadge("Bot C", quality.bot_c)}
    </article>
    <article class="quality-card">
      <span class="stats-label">Ultima actualizacion</span>
      <strong>${escapeHtml(formatTime(quality.last_update || summary.generated_at))}</strong>
      <p class="muted">Snapshot: ${value(quality.latest_snapshot_id)}</p>
    </article>
    <article class="quality-card ${quality.incomplete_metrics ? "quality-card-warning" : ""}">
      <span class="stats-label">Edad del ultimo snapshot</span>
      <strong>${escapeHtml(formatAge(quality.latest_snapshot_age_seconds))}</strong>
      <p class="muted">Timestamp: ${escapeHtml(formatDate(quality.latest_snapshot_timestamp))}</p>
      ${warning}
    </article>
  `;
}

function moduleStatus(label, status, detail, href) {
  const statusKey = String(status || "pending").toLowerCase().replaceAll(" ", "_");
  return `
    <a class="magi-module-card module-status-${escapeHtml(statusKey)}" href="${href}">
      <span class="module-role">${escapeHtml(label)}</span>
      <strong>${escapeHtml(status || "sin datos")}</strong>
      <p>${detail}</p>
    </a>
  `;
}

function renderMagiModules(summary) {
  const counts = summary.counts || {};
  const connections = summary.connections || {};
  const metrics = summary.metrics || {};
  const botCDetail = summary.data_quality?.incomplete_metrics
    ? "Auditoria pendiente o incompleta para cierres reales"
    : `Eventos auditados: ${counts.bot_c?.total_count ?? "no disponible"}`;

  document.getElementById("magiModules").innerHTML = [
    moduleStatus("Bot A | Senales", connections.bot_a, `Total real del rango: ${counts.bot_a?.total_count ?? "no disponible"}`, "/bot_A"),
    moduleStatus("CEO-MAGI | Decisiones", connections.magi, `Decisiones generadas: ${counts.magi?.total_count ?? "no disponible"}`, "/magi"),
    moduleStatus("Bot B | Ejecucion", connections.bot_b, `Payloads retornados: ${counts.bot_b?.returned_count ?? "no disponible"}`, "/bot_B"),
    moduleStatus("Bot C | Auditoria MT5", connections.bot_c, botCDetail, "/bot_C"),
    moduleStatus("Operacion actual", summary.current_position?.status || "unknown", `Abiertas: ${metrics.open_operations ?? "no disponible"}`, "/dashboard"),
  ].join("");
}

function currentBackendUptimeSeconds(summary) {
  const backend = summary?.backend || {};
  if (backend.started_at) {
    const startedAt = new Date(backend.started_at);
    if (!Number.isNaN(startedAt.getTime())) {
      return Math.floor((Date.now() - startedAt.getTime()) / 1000);
    }
  }
  return backend.uptime_seconds;
}

function updateDashboardClock() {
  if (!lastSummary || page !== "dashboard") {
    return;
  }

  const uptimeTarget = document.getElementById("backendUptime");
  if (uptimeTarget) {
    uptimeTarget.textContent = formatDuration(currentBackendUptimeSeconds(lastSummary));
  }

  if (nextRefresh) {
    const remaining = Math.max(0, Math.ceil((nextRefreshAt - Date.now()) / 1000));
    nextRefresh.textContent = `Proxima actualizacion en: ${remaining}s`;
  }
}

function renderDashboard(summary) {
  const current = summary.current_position || {};
  const mode = summary.connections?.magi === "operativo" ? "observacion" : "sin datos";
  const uptime = formatDuration(currentBackendUptimeSeconds(summary));
  const metrics = summary.metrics || {};
  const decisionTotal = summary.counts?.magi?.total_count ?? null;
  const signalTotal = summary.counts?.bot_a?.total_count ?? null;
  const botCQuality = summary.data_quality?.bot_c || "no_disponible";

  document.getElementById("executiveHero").innerHTML = `
    <article class="system-panel cinematic-hero">
      <div class="cinematic-hero-copy">
        <span class="stats-label">Centro de mando MAGI</span>
        <strong>${escapeHtml(mode)}</strong>
        <p class="muted">Posicion: ${escapeHtml(current.status || "no disponible")} | fuente ${escapeHtml(current.source || "no disponible")} | Bot C ${escapeHtml(botCQuality === "disponible" ? "disponible" : "no disponible")}</p>
        <p class="muted">MAGI encendido hace: <span id="backendUptime" class="mono">${escapeHtml(uptime)}</span></p>
      </div>
      <div class="cinematic-hero-orbit" aria-hidden="true">
        <img src="/assets/logo.png" alt="" />
      </div>
      <div class="hero-indicators">
        <span><b>${value(signalTotal)}</b><em>senales</em></span>
        <span><b>${value(decisionTotal)}</b><em>decisiones</em></span>
        <span><b>${value(metrics.open_operations)}</b><em>abiertas</em></span>
      </div>
      <span class="badge ${badgeClass(mode)}">${escapeHtml(mode)}</span>
    </article>
  `;

  const connections = summary.connections || {};
  document.getElementById("connectionStrip").innerHTML = ["bot_a", "magi", "bot_b", "bot_c"]
    .map((key) => `<span class="connection-pill"><b>${key.replace("_", " ").toUpperCase()}</b><em class="${badgeClass(connections[key])}">${escapeHtml(connections[key] || "sin_datos")}</em></span>`)
    .join("");

  renderMagiModules(summary);
  renderDataQuality(summary);

  document.getElementById("executiveMetrics").innerHTML = [
    statusCard("Senales recibidas", value(metrics.signals_received), `Total real del rango | devueltos ${summary.counts?.bot_a?.returned_count ?? "n/a"}/${summary.counts?.bot_a?.limit ?? "n/a"}`, "neutral"),
    statusCard("Decisiones", value(metrics.decisions_generated), `Total real del rango | devueltos ${summary.counts?.magi?.returned_count ?? "n/a"}/${summary.counts?.magi?.limit ?? "n/a"}`, "neutral"),
    statusCard("Operaciones abiertas", value(metrics.open_operations), "Fuente posicion actual/Bot C", current.status === "open" ? "ok" : "neutral"),
    statusCard("Operaciones cerradas", value(metrics.closed_operations), "Solo fuente con profit real", "neutral"),
    statusCard("Ganadoras", value(metrics.winners), "profit > 0", "neutral"),
    statusCard("Perdedoras", value(metrics.losers), "profit < 0", "neutral"),
    statusCard("Breakeven", value(metrics.breakeven), "profit = 0", "neutral"),
    statusCard("PnL diario", numberValue(metrics.daily_pnl), "solo trades cerrados con profit", "neutral"),
    statusCard("Drawdown diario", numberValue(metrics.daily_drawdown), "derivado de curva PnL real", "neutral"),
    statusCard("Profit factor", numberValue(metrics.profit_factor), "si hay ganancias y perdidas reales", "neutral"),
    statusCard("Win rate", numberValue(metrics.win_rate), "si hay trades cerrados con profit", "neutral"),
  ].join("");

  document.getElementById("chartGrid").innerHTML = [
    renderBars(summary.charts?.signals_by_bucket, rangeFilter?.value === "day" ? "Senales por hora" : "Senales por dia"),
    renderBars(summary.charts?.decisions_by_action, "Decisiones por accion"),
    renderSparkline(summary.charts?.pnl_curve, "Curva profit/PnL"),
    renderSparkline(summary.charts?.drawdown_curve, "Curva drawdown"),
    renderWinLossChart(summary.charts?.win_loss),
  ].join("");

  const recent = summary.recent || {};
  document.getElementById("recentGrid").innerHTML = [
    compactList("Bot A", recent.bot_a || [], "/bot_A", (item) => `<div class="recent-row"><b>${value(item.symbol)}</b><span>${formatDate(item.timestamp)}</span><small>${value(item.snapshot_id)}</small></div>`),
    compactList("MAGI", recent.magi || [], "/magi", (item) => `<div class="recent-row"><b>${value(item.final_action)}</b><span>${formatDate(item.timestamp)}</span><small>${value(item.decision_id)}</small></div>`),
    compactList("Bot B", recent.bot_b || [], "/bot_B", (item) => `<div class="recent-row"><b>${value(item.action)}</b><span>${formatDate(item.timestamp)}</span><small>${value(item.comment)}</small></div>`),
    compactList("Bot C", recent.bot_c || [], "/bot_C", (item) => `<div class="recent-row ${item.missing_decision_id ? "audit-row-warning" : ""}"><b>${value(item.event_type)}</b><span>${formatDate(item.timestamp)}</span><small>${value(item.decision_id)}</small></div>`),
  ].join("");
}

function renderTable(columns, items) {
  const target = document.getElementById("recordsTable");
  if (!items.length) {
    target.innerHTML = '<article class="empty-state"><strong>No hay registros disponibles</strong><p class="muted">La fuente no tiene datos reales para mostrar.</p></article>';
    return;
  }

  target.innerHTML = `
    <div class="table-shell command-table-shell">
      <table class="data-table command-table">
        <thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr></thead>
        <tbody>
          ${items.map((item) => `<tr class="${item.missing_decision_id ? "audit-row-warning" : ""}">${columns.map((column) => `<td>${column.render(item)}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function loadRecords() {
  if (page === "bot_A") {
    const payload = await fetchJson("/api/bot-a/events?limit=100");
    renderTable([
      { label: "Timestamp", render: (item) => formatDate(item.timestamp) },
      { label: "Symbol", render: (item) => value(item.symbol) },
      { label: "Snapshot", render: (item) => `<span class="mono">${value(item.snapshot_id)}</span>` },
      { label: "Status", render: (item) => `<span class="badge ${badgeClass(item.status)}">${value(item.status)}</span>` },
      { label: "Source", render: (item) => value(item.source_mode) },
      { label: "Validation", render: (item) => value(item.validation_status) },
      { label: "Issues/Warnings", render: (item) => value([...(item.issues || []), ...(item.warnings || [])].join(" | ")) },
      { label: "Precio", render: (item) => value(item.current_price) },
      { label: "Timeframe", render: (item) => value([item.anchor_timeframe, item.primary_timeframe].filter(Boolean).join(" / ")) },
    ], payload.items || []);
  }

  if (page === "magi") {
    const payload = await fetchJson("/api/magi/decisions?limit=100");
    renderTable([
      { label: "Timestamp", render: (item) => formatDate(item.timestamp) },
      { label: "Decision", render: (item) => `<span class="mono">${value(item.decision_id)}</span>` },
      { label: "Snapshot", render: (item) => `<span class="mono">${value(item.snapshot_id)}</span>` },
      { label: "Symbol", render: (item) => value(item.symbol) },
      { label: "Accion", render: (item) => `<span class="badge ${badgeClass(item.final_action)}">${value(item.final_action)}</span>` },
      { label: "Razon", render: (item) => value(item.reason) },
      { label: "Votos", render: (item) => value(["Melchor", "Baltasar", "Gaspar"].map((name) => `${name}: ${item.votes?.[name.toLowerCase()] ? "si" : "no"}`).join(" | ")) },
      { label: "Payload Bot B", render: (item) => `<span class="mono compact-cell">${escapeHtml(JSON.stringify(item.payload_bot_b || null))}</span>` },
      { label: "Confidence", render: (item) => value(item.confidence) },
    ], payload.items || []);
  }

  if (page === "bot_B") {
    const payload = await fetchJson("/api/bot-b/events?limit=100");
    renderTable([
      { label: "Timestamp", render: (item) => formatDate(item.timestamp) },
      { label: "Symbol", render: (item) => value(item.symbol) },
      { label: "Action", render: (item) => `<span class="badge ${badgeClass(item.action)}">${value(item.action)}</span>` },
      { label: "Decision", render: (item) => `<span class="mono">${value(item.decision_id)}</span>` },
      { label: "Status", render: (item) => value(item.status) },
      { label: "Comment MAGI", render: (item) => value(item.comment) },
      { label: "Errores/Rechazos", render: (item) => value((item.errors || []).join(" | ")) },
      { label: "Dedupe", render: (item) => value(item.dedupe) },
    ], payload.items || []);
  }

  if (page === "bot_C") {
    const payload = await fetchJson("/api/bot-c/events?limit=100");
    renderTable([
      { label: "Tipo", render: (item) => `<span class="badge ${badgeClass(item.event_type)}">${value(item.event_type)}</span>` },
      { label: "Timestamp", render: (item) => formatDate(item.timestamp) },
      { label: "Ticket MT5", render: (item) => `<span class="mono">${value(item.ticket)}</span>` },
      { label: "Symbol", render: (item) => value(item.symbol) },
      { label: "Magic", render: (item) => value(item.magic_number) },
      { label: "Comment", render: (item) => value(item.comment) },
      { label: "Decision ID", render: (item) => item.missing_decision_id ? '<span class="badge badge-danger">sin decision_id</span>' : `<span class="mono">${value(item.decision_id)}</span>` },
      { label: "Profit", render: (item) => numberValue(item.profit) },
      { label: "Anomalias", render: (item) => value(item.anomaly) },
    ], payload.events || []);
  }
}

async function load() {
  if (isLoading) {
    return;
  }

  isLoading = true;
  refreshButton.disabled = true;
  if (refreshStatus) {
    refreshStatus.textContent = "actualizando";
    refreshStatus.classList.remove("refresh-error");
  }

  try {
    if (page === "dashboard") {
      const summary = await fetchJson(`/api/platform/summary?range=${rangeFilter?.value || "day"}`);
      lastSummary = summary;
      renderDashboard(summary);
      nextRefreshAt = Date.now() + dashboardRefreshSeconds * 1000;
      if (lastRefresh) {
        lastRefresh.textContent = `Ultima actualizacion: ${formatTime(summary.generated_at)}`;
      }
      if (refreshStatus) {
        refreshStatus.textContent = "auto activo";
      }
      updateDashboardClock();
    } else {
      await loadRecords();
    }
  } catch (error) {
    if (page === "dashboard" && refreshStatus) {
      refreshStatus.textContent = "error de actualizacion";
      refreshStatus.classList.add("refresh-error");
      nextRefreshAt = Date.now() + dashboardRefreshSeconds * 1000;
      if (!lastSummary) {
        document.getElementById("executiveHero").innerHTML = `<article class="empty-state error-state"><strong>Error de actualizacion</strong><p class="muted">${escapeHtml(error.message)}</p></article>`;
      }
    } else {
      throw error;
    }
  } finally {
    refreshButton.disabled = false;
    isLoading = false;
  }
}

function setupDashboardAutoRefresh() {
  if (page !== "dashboard") {
    return;
  }

  autoRefreshTimer = window.setInterval(() => {
    if (Date.now() >= nextRefreshAt) {
      load();
    }
  }, 1000);

  dashboardClockTimer = window.setInterval(updateDashboardClock, 1000);

  window.addEventListener("beforeunload", () => {
    window.clearInterval(autoRefreshTimer);
    window.clearInterval(dashboardClockTimer);
  });
}

setActiveNav();
refreshButton?.addEventListener("click", () => {
  nextRefreshAt = Date.now() + dashboardRefreshSeconds * 1000;
  load();
});
rangeFilter?.addEventListener("change", () => {
  nextRefreshAt = Date.now() + dashboardRefreshSeconds * 1000;
  load();
});
setupDashboardAutoRefresh();
load().catch((error) => {
  const target = document.getElementById("recordsTable") || document.getElementById("executiveHero");
  target.innerHTML = `<article class="empty-state error-state"><strong>Error cargando datos</strong><p class="muted">${escapeHtml(error.message)}</p></article>`;
});
