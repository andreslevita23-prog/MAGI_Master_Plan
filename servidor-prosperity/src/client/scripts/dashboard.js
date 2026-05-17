const refreshButton = document.getElementById("refreshButton");
const lastRefresh = document.getElementById("lastRefresh");
const navLinks = Array.from(document.querySelectorAll(".nav-link"));

const unavailable = '<span class="data-missing">dato no disponible</span>';

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function valueOrMissing(value, suffix = "") {
  if (value === null || value === undefined || value === "" || Number.isNaN(value)) {
    return unavailable;
  }

  return `${escapeHtml(value)}${suffix}`;
}

function numberOrMissing(value, digits = 2, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return unavailable;
  }

  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return unavailable;
  }

  return `${numeric.toFixed(digits)}${suffix}`;
}

function formatDate(value) {
  if (!value) {
    return "dato no disponible";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

function formatAge(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.getTime())) {
    return "dato no disponible";
  }

  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function formatSeconds(seconds) {
  const totalSeconds = Number(seconds);
  if (!Number.isFinite(totalSeconds)) {
    return "dato no disponible";
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = Math.floor(totalSeconds % 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  return `${remainingSeconds}s`;
}

function formatUptime(seconds = 0) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function badgeClass(status) {
  const key = String(status || "").toLowerCase();
  if (["operativo", "recibiendo", "activo", "connected", "ok", "allow", "demo_activo", "disponible", "open"].includes(key)) {
    return "badge-ok";
  }
  if (["observacion", "sin_datos", "warning", "hold", "pendiente", "partial", "sin_archivos", "unknown", "closed"].includes(key)) {
    return "badge-warning";
  }
  if (["error", "offline", "blocked", "bloqueado", "pausado", "no_disponible", "not_available"].includes(key)) {
    return "badge-danger";
  }
  return "badge-neutral";
}

function actionLabel(action) {
  const map = {
    hold: "HOLD",
    open: "OPEN",
    close: "CLOSE",
    modify: "MODIFY",
    buy: "BUY",
    sell: "SELL",
  };

  return map[String(action || "").toLowerCase()] || String(action || "dato no disponible").toUpperCase();
}

function inferMagiMode(overview, latestExecution, logs) {
  if (logs?.total_errors > 0) {
    return { label: "observacion con alertas", status: "warning" };
  }

  if (!overview?.snapshots?.latest) {
    return { label: "observacion", status: "warning" };
  }

  if (latestExecution?.final_action && latestExecution.final_action !== "hold") {
    return { label: "demo activo", status: "ok" };
  }

  return { label: "observacion", status: "warning" };
}

function StatusCard({ label, value, detail, status = "neutral" }) {
  return `
    <article class="status-card status-${escapeHtml(status)}">
      <span class="stats-label">${escapeHtml(label)}</span>
      <strong>${value}</strong>
      <p class="muted">${detail}</p>
    </article>
  `;
}

function ConnectionBadge({ name, status, detail }) {
  return `
    <article class="connection-card">
      <div>
        <span class="stats-label">${escapeHtml(name)}</span>
        <strong><span class="badge ${badgeClass(status)}">${escapeHtml(status)}</span></strong>
      </div>
      <p class="muted">${detail}</p>
    </article>
  `;
}

function CurrentPositionPanel({ position }) {
  const status = position?.status || "not_available";
  const hasOpenPosition = status === "open";
  const operationStatus = {
    open: "operacion abierta",
    closed: "sin operacion abierta",
    unknown: "estado desconocido",
    not_available: "posicion no disponible",
  }[status] || "estado desconocido";
  const warnings = position?.warnings || [];

  return `
    <article class="position-panel">
      <div class="position-header">
        <div>
          <span class="stats-label">Estado</span>
          <h4>${escapeHtml(operationStatus)}</h4>
          <p class="muted">Fuente: <span class="mono">${valueOrMissing(position?.source)}</span> | confianza: ${valueOrMissing(position?.confidence)}</p>
        </div>
        <span class="badge ${hasOpenPosition ? "badge-open" : badgeClass(status)}">${escapeHtml(status.toUpperCase())}</span>
      </div>
      <div class="detail-grid">
        <div><span class="stats-label">Simbolo</span><strong>${valueOrMissing(position?.symbol)}</strong></div>
        <div><span class="stats-label">Ticket</span><strong class="mono">${valueOrMissing(position?.ticket)}</strong></div>
        <div><span class="stats-label">BUY/SELL</span><strong>${valueOrMissing(position?.side)}</strong></div>
        <div><span class="stats-label">Entrada</span><strong>${valueOrMissing(position?.entry_price)}</strong></div>
        <div><span class="stats-label">SL</span><strong>${valueOrMissing(position?.sl)}</strong></div>
        <div><span class="stats-label">TP</span><strong>${valueOrMissing(position?.tp)}</strong></div>
        <div><span class="stats-label">Lotaje</span><strong>${valueOrMissing(position?.lot_size)}</strong></div>
        <div><span class="stats-label">Profit flotante</span><strong>${numberOrMissing(position?.floating_profit, 2)}</strong></div>
        <div><span class="stats-label">Apertura</span><strong>${position?.open_time ? formatDate(position.open_time) : unavailable}</strong></div>
        <div><span class="stats-label">Duracion</span><strong>${position?.duration_seconds === null || position?.duration_seconds === undefined ? unavailable : formatSeconds(position.duration_seconds)}</strong></div>
        <div><span class="stats-label">Decision ID</span><strong class="mono">${valueOrMissing(position?.decision_id)}</strong></div>
        <div><span class="stats-label">Snapshot ID</span><strong class="mono">${valueOrMissing(position?.snapshot_id)}</strong></div>
        <div><span class="stats-label">Proteccion</span><strong>${valueOrMissing(position?.protection_state)}</strong></div>
      </div>
      <div class="position-notes">
        <div>
          <span class="stats-label">Comment MAGI</span>
          <p class="mono">${valueOrMissing(position?.comment)}</p>
        </div>
        <div>
          <span class="stats-label">Advertencias</span>
          <p>${warnings.length ? warnings.map((warning) => escapeHtml(warning)).join("<br />") : "sin advertencias"}</p>
        </div>
      </div>
    </article>
  `;
}

function DecisionTimeline(items) {
  if (!items.length) {
    return `<article class="empty-state"><strong>Sin decisiones registradas</strong><p class="muted">Cuando Bot A envie snapshots, CEO-MAGI guardara aqui la bitacora.</p></article>`;
  }

  return `
    <div class="table-shell command-table-shell">
      <table class="data-table command-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Snapshot</th>
            <th>Decision</th>
            <th>Simbolo</th>
            <th>Accion final</th>
            <th>Razon</th>
            <th>Votos</th>
            <th>Payload Bot B</th>
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          ${items
            .map((item) => {
              const response = item.bot_b_response || {};
              const details = response.details || {};
              const votes = [
                item.melchor_vote ? `Melchor: ${item.melchor_vote.vote || "disponible"}` : "Melchor: no disponible",
                item.baltasar_vote ? "Baltasar: disponible" : "Baltasar: no disponible",
                item.gaspar_vote ? "Gaspar: disponible" : "Gaspar: no disponible",
              ].join("<br />");

              return `
                <tr>
                  <td>${formatDate(item.stored_at || response.decision_time || response.timestamp)}</td>
                  <td class="mono">${valueOrMissing(item.snapshot_id)}</td>
                  <td class="mono">${valueOrMissing(response.decision_id || item.decision_id)}</td>
                  <td>${valueOrMissing(item.symbol)}</td>
                  <td><span class="badge ${badgeClass(item.final_action)}">${escapeHtml(actionLabel(item.final_action))}</span></td>
                  <td>${valueOrMissing(item.reason)}</td>
                  <td>${votes}</td>
                  <td class="mono compact-cell">${escapeHtml(JSON.stringify(response || null))}</td>
                  <td>${response.action ? "enviado a Bot B" : "dato no disponible"}</td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function BotCAuditTable(botC) {
  const events = botC?.events || [];
  const source = botC?.audit_root ? escapeHtml(botC.audit_root) : "ruta Bot C no configurada";
  const reason = botC?.reason ? escapeHtml(botC.reason) : "archivo Bot C no disponible para el backend";

  if (!events.length) {
    return `
      <article class="empty-state audit-empty">
        <strong>Sin eventos reales de Bot C disponibles</strong>
        <p class="muted">${reason}</p>
        <p class="muted">Ruta auditada: <span class="mono">${source}</span>.</p>
        <p class="muted">Cuando MT5 escriba <span class="mono">bot_c_events.jsonl</span>, esta tabla resaltara aperturas, cierres, modificaciones y eventos sin <span class="mono">decision_id</span>.</p>
      </article>
    `;
  }

  return `
    <div class="table-shell command-table-shell">
      <table class="data-table command-table">
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Timestamp</th>
            <th>Ticket</th>
            <th>Symbol</th>
            <th>Magic</th>
            <th>Comment</th>
            <th>Decision ID</th>
            <th>Profit final</th>
            <th>Anomalia</th>
          </tr>
        </thead>
        <tbody>
          ${events
            .map((event) => {
              const missingDecision = !event.decision_id;
              return `
                <tr class="${missingDecision ? "audit-row-warning" : ""}">
                  <td><span class="badge ${badgeClass(event.event_type || event.type)}">${valueOrMissing(event.event_type || event.type)}</span></td>
                  <td>${formatDate(event.timestamp)}</td>
                  <td class="mono">${valueOrMissing(event.ticket)}</td>
                  <td>${valueOrMissing(event.symbol)}</td>
                  <td class="mono">${valueOrMissing(event.magic_number)}</td>
                  <td class="mono">${valueOrMissing(event.comment)}</td>
                  <td class="mono">${missingDecision ? '<span class="badge badge-danger">sin decision_id</span>' : valueOrMissing(event.decision_id)}</td>
                  <td>${numberOrMissing(event.profit, 2)}</td>
                  <td>${valueOrMissing(event.anomaly || event.error || event.anomaly_type)}</td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function SafetyModePanel(mode, governance = {}) {
  const risk = governance.risk_state || {};
  const cluster = governance.cluster_state || {};
  const shadow = governance.shadow_guardrails || {};
  const modes = [
    ["solo_observacion", "Solo observacion", mode === "observacion"],
    ["demo_activo", "Demo activo", mode === "demo activo"],
    ["safe_mode", "SAFE_MODE", Boolean(risk.safe_mode_active)],
  ];

  const dangerous = [
    "Bloquear operaciones por hoy",
    "Cerrar todo",
  ];

  return `
    <div class="safety-grid">
      <article class="safety-card">
        <span class="stats-label">Modo actual inferido</span>
        <strong>${escapeHtml(mode)}</strong>
        <p class="muted">Inferido desde snapshots, decisiones y errores. No modifica backend ni trading.</p>
      </article>
      <article class="safety-card">
        <span class="stats-label">Gobernanza operativa</span>
        <div class="safety-controls">
          ${modes
            .map(
              ([id, label, checked]) => `
                <label class="safety-toggle" for="${id}">
                  <input id="${id}" type="checkbox" ${checked ? "checked" : ""} disabled />
                  <span>${label}</span>
                </label>
              `,
            )
            .join("")}
        </div>
        <p class="muted">Lotaje demo: ${valueOrMissing(governance.current_lot_size)} | hasta ${valueOrMissing(governance.demo_mode_until)}</p>
        <p class="muted">Cluster: ${escapeHtml((cluster.sequence || risk.cluster_sequence || []).join("-") || "sin cluster")} | SL consecutivos: ${valueOrMissing(cluster.consecutive_sl ?? risk.cluster_consecutive_sl)}</p>
      </article>
      <article class="safety-card danger-zone">
        <span class="stats-label">Shadow guardrails</span>
        <p class="muted">Friday would block: ${shadow.friday_guardrail_would_block ? "SI" : "NO"}</p>
        <p class="muted">Cluster 2SL would block: ${shadow.cluster_2sl_would_block ? "SI" : "NO"}</p>
        <div class="safety-actions">${dangerous.map((label) => `<button class="button button-danger" disabled>${label}<small>requiere operador</small></button>`).join("")}</div>
      </article>
    </div>
  `;
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${path} respondio ${response.status}`);
  }

  return response.json();
}

async function loadSnapshotDetail(snapshotId) {
  if (!snapshotId) {
    return null;
  }

  try {
    return await fetchJson(`/api/snapshots/${encodeURIComponent(snapshotId)}`);
  } catch {
    return null;
  }
}

function buildConnections(overview, latestExecution, botC) {
  return [
    {
      name: "Bot A",
      status: overview?.bot_a?.status || "sin_datos",
      detail: `Ultimo snapshot: ${escapeHtml(overview?.bot_a?.last_snapshot_id || "dato no disponible")} | hace ${formatAge(overview?.bot_a?.last_received_at)}`,
    },
    {
      name: "Backend CEO-MAGI",
      status: overview?.status || "sin_datos",
      detail: `Servicio ${escapeHtml(overview?.service || "desconocido")} | uptime ${formatUptime(overview?.uptime_seconds || 0)}`,
    },
    {
      name: "Bot B",
      status: latestExecution?.bot_b_response ? "connected" : "sin_datos",
      detail: latestExecution?.bot_b_response
        ? `Ultima salida: ${escapeHtml(actionLabel(latestExecution.final_action))} para ${escapeHtml(latestExecution.symbol || "-")}`
        : "No hay payload reciente enviado a Bot B.",
    },
    {
      name: "Bot C",
      status: botC?.status === "disponible" ? "connected" : "sin_datos",
      detail: botC?.status === "disponible"
        ? `${botC.total_events} eventos MT5 disponibles; ${botC.missing_decision_id} sin decision_id.`
        : "Sin auditoria real Bot C disponible para la fecha actual.",
    },
  ];
}

function renderDashboard({ overview, snapshots, execution, logs, botC, currentPosition, governance, latestSnapshotDetail }) {
  const latestSnapshot = snapshots.latest || overview.snapshots?.latest || null;
  const latestExecution = execution.latest || execution.items?.[0] || null;
  const latestResponse = latestExecution?.bot_b_response || {};
  const account = latestSnapshotDetail?.normalized?.account || null;
  const risk = latestSnapshotDetail?.normalized?.risk || account || null;
  const mode = inferMagiMode(overview, latestExecution, logs);
  const hasOpenPosition = currentPosition?.status === "open";

  document.getElementById("systemHero").innerHTML = `
    <article class="system-panel">
      <div>
        <span class="stats-label">Estado general MAGI</span>
        <strong>${escapeHtml(mode.label)}</strong>
        <p class="muted">Backend ${escapeHtml(overview.service || "prosperity-magi")} | actualizado ${formatDate(overview.timestamp)}</p>
      </div>
      <div class="hero-indicators">
        <span class="badge ${badgeClass(mode.status)}">${escapeHtml(mode.label)}</span>
        <span class="badge ${hasOpenPosition ? "badge-open" : "badge-neutral"}">${hasOpenPosition ? "hay operacion abierta" : "sin operacion abierta"}</span>
      </div>
    </article>
  `;

  document.getElementById("statusCards").innerHTML = [
    StatusCard({
      label: "Ultima senal recibida",
      value: valueOrMissing(latestSnapshot?.symbol),
      detail: `Snapshot ${escapeHtml(latestSnapshot?.snapshot_id || "dato no disponible")} | ${formatDate(latestSnapshot?.received_at)}`,
      status: latestSnapshot ? "ok" : "warning",
    }),
    StatusCard({
      label: "Ultima decision CEO-MAGI",
      value: `<span class="badge ${badgeClass(latestExecution?.final_action)}">${escapeHtml(actionLabel(latestExecution?.final_action))}</span>`,
      detail: escapeHtml(latestExecution?.reason || "dato no disponible"),
      status: latestExecution?.final_action === "hold" ? "warning" : "ok",
    }),
    StatusCard({
      label: "Operacion abierta",
      value: hasOpenPosition ? "SI" : "NO",
      detail: hasOpenPosition ? "Bot A reporta posicion abierta." : "El ultimo snapshot no reporta posicion abierta.",
      status: hasOpenPosition ? "ok" : "neutral",
    }),
    StatusCard({
      label: "PnL del dia",
      value: unavailable,
      detail: "Endpoint de PnL diario no disponible en Fase 1.",
      status: "neutral",
    }),
    StatusCard({
      label: "Drawdown diario",
      value: risk?.daily_drawdown_percent === 0 ? "0.00% (placeholder)" : numberOrMissing(risk?.daily_drawdown_percent, 2, "%"),
      detail: risk?.daily_drawdown_percent === 0 ? "Bot A lo envia como 0.0; pendiente validar dato real." : "Dato tomado del ultimo snapshot.",
      status: risk?.daily_drawdown_percent ? "warning" : "neutral",
    }),
    StatusCard({
      label: "Riesgo por trade",
      value: risk?.risk_percent_per_trade === 0 ? "0.00% (placeholder)" : numberOrMissing(risk?.risk_percent_per_trade, 2, "%"),
      detail: "Disponible solo si Bot A lo informa en snapshot.",
      status: "neutral",
    }),
    StatusCard({
      label: "Ultimo snapshot_id",
      value: `<span class="mono">${valueOrMissing(latestSnapshot?.snapshot_id)}</span>`,
      detail: `Contexto: ${escapeHtml(latestSnapshot?.context || "dato no disponible")}`,
      status: latestSnapshot ? "ok" : "warning",
    }),
    StatusCard({
      label: "Ultimo decision_id",
      value: `<span class="mono">${valueOrMissing(latestResponse.decision_id)}</span>`,
      detail: `Comment: ${escapeHtml(latestResponse.details?.comment || "dato no disponible")}`,
      status: latestResponse.decision_id ? "ok" : "warning",
    }),
    StatusCard({
      label: "SAFE_MODE",
      value: governance?.risk_state?.safe_mode_active ? "ACTIVO" : "NO",
      detail: governance?.risk_state?.safe_mode_reason || `Cluster SL: ${valueOrMissing(governance?.risk_state?.cluster_consecutive_sl)}`,
      status: governance?.risk_state?.safe_mode_active ? "danger" : "neutral",
    }),
    StatusCard({
      label: "Lotaje demo",
      value: valueOrMissing(governance?.current_lot_size),
      detail: `Demo hasta ${valueOrMissing(governance?.demo_mode_until)}`,
      status: "neutral",
    }),
  ].join("");

  document.getElementById("connectionPanel").innerHTML = buildConnections(overview, latestExecution, botC)
    .map((item) => ConnectionBadge(item))
    .join("");

  document.getElementById("currentPositionPanel").innerHTML = CurrentPositionPanel({ position: currentPosition });

  document.getElementById("decisionTimeline").innerHTML = DecisionTimeline(execution.items || []);
  document.getElementById("botCAuditTable").innerHTML = BotCAuditTable(botC);
  document.getElementById("safetyModePanel").innerHTML = SafetyModePanel(mode.label, governance);
}

async function loadDashboard() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Actualizando";

  try {
    const [overview, snapshots, execution, logs, botC, currentPosition, governance] = await Promise.all([
      fetchJson("/api/overview"),
      fetchJson("/api/snapshots?limit=20"),
      fetchJson("/api/execution"),
      fetchJson("/api/logs"),
      fetchJson("/api/bot-c/audit"),
      fetchJson("/api/position/current"),
      fetchJson("/api/governance"),
    ]);
    const latestSnapshotDetail = await loadSnapshotDetail(snapshots.latest?.snapshot_id || overview.snapshots?.latest?.snapshot_id);

    renderDashboard({ overview, snapshots, execution, logs, botC, currentPosition, governance, latestSnapshotDetail });
    lastRefresh.textContent = `actualizado ${formatDate(new Date().toISOString())}`;
  } catch (error) {
    document.getElementById("systemHero").innerHTML = `
      <article class="empty-state error-state">
        <strong>No fue posible cargar MAGI Command</strong>
        <p class="muted">${escapeHtml(error.message)}</p>
      </article>
    `;
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Actualizar";
  }
}

function syncNavigation() {
  const currentHash = window.location.hash || "#dashboard";
  navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.getAttribute("href") === currentHash);
  });
}

refreshButton?.addEventListener("click", loadDashboard);
window.addEventListener("hashchange", syncNavigation);

syncNavigation();
loadDashboard();
