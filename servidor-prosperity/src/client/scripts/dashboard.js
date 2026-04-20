const navLinks = Array.from(document.querySelectorAll(".nav-link"));
const refreshButton = document.getElementById("refreshButton");

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatDuration(seconds = 0) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours} h ${minutes} min`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildStatusLabel(status) {
  const map = {
    operativo: "badge-ok",
    recibiendo: "badge-ok",
    sin_datos: "badge-warning",
    error: "badge-danger",
    caso_mvp: "badge-ok",
    sin_caso: "badge-neutral",
  };

  return map[status] || "badge-neutral";
}

function formatCaseType(value) {
  const map = {
    entry_case: "Caso de entrada",
    management_case: "Caso de gestion",
  };

  return map[value] || "No aplica";
}

function formatCaseState(value) {
  const map = {
    caso_mvp: "Caso MVP",
    sin_caso: "Sin caso",
  };

  return map[value] || value || "-";
}

function renderOverview(overview) {
  document.getElementById("overviewHero").innerHTML = `
    <article class="overview-panel">
      <div class="overview-copy">
        <span class="stats-label">Estado general</span>
        <strong class="overview-status">${escapeHtml(overview.status)}</strong>
        <p class="muted">Servicio: ${escapeHtml(overview.service)}</p>
        <p class="muted">Ultima actualizacion: ${formatDate(overview.timestamp)}</p>
      </div>
      <div class="overview-meta">
        <div class="overview-item">
          <span class="stats-label">Bot A</span>
          <strong><span class="badge ${buildStatusLabel(overview.bot_a?.status)}">${escapeHtml(overview.bot_a?.status || "sin_datos")}</span></strong>
        </div>
        <div class="overview-item">
          <span class="stats-label">Tiempo activo</span>
          <strong>${formatDuration(overview.uptime_seconds)}</strong>
        </div>
      </div>
    </article>
  `;

  document.getElementById("overviewCards").innerHTML = `
    <article class="stats-card">
      <span class="stats-label">Instantaneas guardadas</span>
      <strong class="stats-value">${overview.snapshots?.total ?? 0}</strong>
      <p class="muted">Cantidad total registrada en persistencia.</p>
    </article>
    <article class="stats-card">
      <span class="stats-label">Ultimo snapshot</span>
      <strong class="stats-value value-sm">${escapeHtml(overview.snapshots?.latest?.snapshot_id || "-")}</strong>
      <p class="muted">Recibido: ${formatDate(overview.bot_a?.last_received_at)}</p>
    </article>
    <article class="stats-card">
      <span class="stats-label">Simbolo activo</span>
      <strong class="stats-value">${escapeHtml(overview.snapshots?.latest?.symbol || "-")}</strong>
      <p class="muted">Contexto: ${escapeHtml(overview.snapshots?.latest?.context || "-")}</p>
    </article>
    <article class="stats-card">
      <span class="stats-label">Estado de validacion</span>
      <strong class="stats-value">${overview.snapshots?.latest?.is_valid ? "Valido" : "Con observaciones"}</strong>
      <p class="muted">Incidencias: ${(overview.snapshots?.latest?.issues || []).length}</p>
    </article>
  `;
}

function renderSnapshots(payload) {
  const list = document.getElementById("snapshotsList");
  const items = payload?.items || [];

  if (!items.length) {
    list.innerHTML = `
      <article class="snapshot-card">
        <span class="stats-label">Sin snapshots</span>
        <p class="muted">Todavia no hay entradas guardadas desde Bot A.</p>
      </article>
    `;
    return;
  }

  list.innerHTML = items
    .map(
      (item) => `
        <article class="snapshot-card">
          <div class="snapshot-head">
            <div>
              <span class="stats-label">Instantanea</span>
              <h4>${escapeHtml(item.snapshot_id)}</h4>
            </div>
            <span class="badge ${item.is_valid ? "badge-ok" : "badge-warning"}">
              ${item.is_valid ? "Valido" : "Con observaciones"}
            </span>
          </div>
          <div class="snapshot-grid">
            <div>
              <span class="stats-label">Simbolo</span>
              <strong>${escapeHtml(item.symbol)}</strong>
            </div>
            <div>
              <span class="stats-label">Precio</span>
              <strong>${escapeHtml(item.price)}</strong>
            </div>
            <div>
              <span class="stats-label">Contexto</span>
              <strong>${escapeHtml(item.context)}</strong>
            </div>
            <div>
              <span class="stats-label">Posicion abierta</span>
              <strong>${item.has_open_position ? "Si" : "No"}</strong>
            </div>
            <div>
              <span class="stats-label">Acciones permitidas</span>
              <strong>${escapeHtml((item.allowed_actions || []).join(", ") || "-")}</strong>
            </div>
            <div>
              <span class="stats-label">Recibido</span>
              <strong>${formatDate(item.received_at)}</strong>
            </div>
          </div>
          <div class="snapshot-foot">
            <p class="muted">Incidencias: ${escapeHtml((item.issues || []).join(" | ") || "ninguna")}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderCases(payload) {
  const list = document.getElementById("casesList");
  const items = payload?.items || [];

  if (!items.length) {
    list.innerHTML = `
      <article class="case-card">
        <span class="stats-label">Sin casos</span>
        <p class="muted">Todavia no hay decisiones MVP registradas en persistencia.</p>
      </article>
    `;
    return;
  }

  list.innerHTML = items
    .map(
      (item) => `
        <article class="case-card">
          <div class="case-head">
            <div>
              <span class="stats-label">Caso</span>
              <h4>${escapeHtml(item.case_id)}</h4>
            </div>
            <span class="badge ${buildStatusLabel(item.case_state)}">${escapeHtml(formatCaseState(item.case_state))}</span>
          </div>
          <div class="case-grid">
            <div>
              <span class="stats-label">Simbolo</span>
              <strong>${escapeHtml(item.symbol)}</strong>
            </div>
            <div>
              <span class="stats-label">Tipo</span>
              <strong>${escapeHtml(formatCaseType(item.case_type))}</strong>
            </div>
            <div>
              <span class="stats-label">Accion final</span>
              <strong>${escapeHtml(item.final_action || "-")}</strong>
            </div>
            <div>
              <span class="stats-label">Disponible para Bot B</span>
              <strong>${item.response_ready ? "Si" : "No"}</strong>
            </div>
          </div>
          <div class="case-foot">
            <p class="muted">Razon principal: ${escapeHtml(item.reason || "sin razon registrada")}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderExecution(payload) {
  const list = document.getElementById("executionList");
  const items = payload?.items || [];

  if (!items.length) {
    list.innerHTML = `
      <article class="execution-card">
        <span class="stats-label">Sin despacho</span>
        <p class="muted">Todavia no hay respuestas preparadas para Bot B.</p>
      </article>
    `;
    return;
  }

  list.innerHTML = items
    .map(
      (item) => `
        <article class="execution-card">
          <div class="case-head">
            <div>
              <span class="stats-label">Respuesta para Bot B</span>
              <h4>${escapeHtml(item.symbol)}</h4>
            </div>
            <span class="badge ${item.bot_b_response?.action === "open" ? "badge-ok" : "badge-neutral"}">${escapeHtml(item.bot_b_response?.action || "hold")}</span>
          </div>
          <div class="execution-grid">
            <div>
              <span class="stats-label">Caso</span>
              <strong>${escapeHtml(formatCaseState(item.case_state))}</strong>
            </div>
            <div>
              <span class="stats-label">Tipo</span>
              <strong>${escapeHtml(formatCaseType(item.case_type))}</strong>
            </div>
            <div>
              <span class="stats-label">Orden</span>
              <strong>${escapeHtml(item.bot_b_response?.details?.order_type || "-")}</strong>
            </div>
            <div>
              <span class="stats-label">Entrada</span>
              <strong>${escapeHtml(item.bot_b_response?.details?.entry_price ?? "-")}</strong>
            </div>
            <div>
              <span class="stats-label">SL</span>
              <strong>${escapeHtml(item.bot_b_response?.details?.stop_loss ?? "-")}</strong>
            </div>
            <div>
              <span class="stats-label">TP</span>
              <strong>${escapeHtml(item.bot_b_response?.details?.take_profit ?? "-")}</strong>
            </div>
          </div>
          <div class="case-foot">
            <p class="muted">Comentario para Bot B: ${escapeHtml(item.bot_b_response?.details?.comment || "sin comentario")}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderLogs(payload) {
  const panel = document.getElementById("logsPanel");
  const events = payload?.events || [];
  const errors = payload?.errors || [];

  panel.innerHTML = `
    <div class="logs-grid">
      <article class="log-card">
        <div class="case-head">
          <div>
            <span class="stats-label">Eventos recientes</span>
            <h4>${events.length}</h4>
          </div>
        </div>
        ${
          events.length
            ? events
              .slice(0, 5)
              .map(
                (item) => `
                  <div class="log-entry-inline">
                    <strong>${escapeHtml(item.event || "evento")}</strong>
                    <p class="muted">${formatDate(item.timestamp_utc)} | ${escapeHtml(item.symbol || "-")}</p>
                  </div>
                `,
              )
              .join("")
            : '<p class="muted">No hay eventos recientes del sistema.</p>'
        }
      </article>
      <article class="log-card">
        <div class="case-head">
          <div>
            <span class="stats-label">Errores recientes</span>
            <h4>${errors.length}</h4>
          </div>
        </div>
        ${
          errors.length
            ? errors
              .slice(0, 5)
              .map(
                (item) => `
                  <div class="log-entry-inline">
                    <strong>${escapeHtml(item.file || "error")}</strong>
                    <p class="muted">${formatDate(item.timestamp)} | ${escapeHtml(String(item.size_bytes || 0))} bytes</p>
                  </div>
                `,
              )
              .join("")
            : '<p class="muted">No hay errores recientes.</p>'
        }
      </article>
    </div>
  `;
}

async function loadDashboard() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Actualizando...";

  try {
    const [overviewResponse, snapshotsResponse, casesResponse, executionResponse, logsResponse] = await Promise.all([
      fetch("/api/overview"),
      fetch("/api/snapshots?limit=12"),
      fetch("/api/cases"),
      fetch("/api/execution"),
      fetch("/api/logs"),
    ]);

    if (!overviewResponse.ok || !snapshotsResponse.ok || !casesResponse.ok || !executionResponse.ok || !logsResponse.ok) {
      throw new Error("No fue posible cargar los datos del centro de mando.");
    }

    const overview = await overviewResponse.json();
    const snapshots = await snapshotsResponse.json();
    const cases = await casesResponse.json();
    const execution = await executionResponse.json();
    const logs = await logsResponse.json();

    renderOverview(overview);
    renderSnapshots(snapshots);
    renderCases(cases);
    renderExecution(execution);
    renderLogs(logs);
  } catch (error) {
    document.getElementById("overviewHero").innerHTML = `
      <article class="stats-card">
        <span class="stats-label">Error</span>
        <strong class="stats-value value-sm">No fue posible cargar el estado del sistema.</strong>
      </article>
    `;
    document.getElementById("overviewCards").innerHTML = "";
    document.getElementById("snapshotsList").innerHTML = `
      <article class="snapshot-card">
        <span class="stats-label">Error</span>
        <p class="muted">${escapeHtml(error.message)}</p>
      </article>
    `;
    document.getElementById("casesList").innerHTML = `
      <article class="case-card">
        <span class="stats-label">Error</span>
        <p class="muted">${escapeHtml(error.message)}</p>
      </article>
    `;
    document.getElementById("executionList").innerHTML = `
      <article class="execution-card">
        <span class="stats-label">Error</span>
        <p class="muted">${escapeHtml(error.message)}</p>
      </article>
    `;
    document.getElementById("logsPanel").innerHTML = "";
    console.error(error);
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Actualizar datos";
  }
}

function syncNavigation() {
  const currentHash = window.location.hash || "#estado";

  navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.getAttribute("href") === currentHash);
  });
}

refreshButton?.addEventListener("click", loadDashboard);
window.addEventListener("hashchange", syncNavigation);

syncNavigation();
loadDashboard();
