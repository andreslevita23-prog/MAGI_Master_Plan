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
  return `${hours}h ${minutes}m`;
}

function renderOverview(overview) {
  const cards = [
    { label: "System status", value: overview.systemStatus },
    { label: "Tracked symbols", value: overview.trackedSymbols },
    { label: "Active signals", value: overview.activeSignals },
    { label: "Uptime", value: formatDuration(overview.uptimeSeconds) },
    { label: "Last decision", value: formatDate(overview.lastDecisionAt) },
    { label: "Latest log folder", value: overview.latestFolder || "-" },
  ];

  document.getElementById("overviewCards").innerHTML = cards
    .map(
      (card) => `
        <article class="stats-card">
          <span class="stats-label">${card.label}</span>
          <strong class="stats-value">${card.value}</strong>
        </article>
      `,
    )
    .join("");
}

function renderModules(modules) {
  document.getElementById("moduleCards").innerHTML = modules
    .map(
      (module) => `
        <article class="module-card">
          <span class="module-role">${module.role}</span>
          <h4>${module.name}</h4>
          <p class="muted">${module.description}</p>
          <span class="module-status">${module.status}</span>
          <p class="muted">${module.metric}</p>
        </article>
      `,
    )
    .join("");
}

function badgeClass(action) {
  return `badge-${String(action).toLowerCase().replace(/\s+/g, "-")}`;
}

function renderSignals(signals) {
  const table = document.getElementById("signalsTable");

  if (!signals.length) {
    table.innerHTML = `
      <tr>
        <td colspan="6" class="muted">Todavia no hay decisiones registradas.</td>
      </tr>
    `;
    return;
  }

  table.innerHTML = signals
    .map(
      (signal) => `
        <tr>
          <td class="mono">${formatDate(signal.timestamp)}</td>
          <td>${signal.symbol}</td>
          <td><span class="badge ${badgeClass(signal.action)}">${signal.action}</span></td>
          <td>${signal.orderType || "-"}</td>
          <td>${signal.lotSize}</td>
          <td>${signal.comment}</td>
        </tr>
      `,
    )
    .join("");
}

function renderLogs(logs) {
  const node = document.getElementById("logFeed");

  if (!logs.length) {
    node.innerHTML = `<article class="log-entry"><strong>Sin logs recientes</strong></article>`;
    return;
  }

  node.innerHTML = logs
    .map(
      (log) => `
        <article class="log-entry">
          <span class="log-source">${log.source}</span>
          <strong>${formatDate(log.timestamp)}</strong>
          <p>${String(log.summary).slice(0, 220)}</p>
        </article>
      `,
    )
    .join("");
}

function renderSettings(settings) {
  const cards = [
    {
      key: "Environment",
      body: `<strong>${settings.environment}</strong><p class="muted">URL prevista: ${settings.siteUrl}</p>`,
    },
    {
      key: "Connectivity",
      body: `<strong>OpenAI configurado: ${settings.openAIConfigured ? "si" : "no"}</strong><p class="muted">Mocks habilitados: ${settings.mocksEnabled ? "si" : "no"}</p>`,
    },
    {
      key: "Storage",
      body: `<strong class="mono">${settings.storage.analysis}</strong><p class="muted">Logs: ${settings.storage.logs}</p><p class="muted">Errores: ${settings.storage.errors}</p>`,
    },
    {
      key: "Future connections",
      body: `<ul>${settings.futureConnections
        .map((item) => `<li>${item}</li>`)
        .join("")}</ul>`,
    },
  ];

  document.getElementById("settingsPanel").innerHTML = cards
    .map(
      (card) => `
        <article class="setting-card">
          <span class="setting-key">${card.key}</span>
          ${card.body}
        </article>
      `,
    )
    .join("");
}

async function loadDashboard() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Actualizando...";

  try {
    const response = await fetch("/api/dashboard");
    const payload = await response.json();

    renderOverview(payload.overview);
    renderModules(payload.modules);
    renderSignals(payload.signals);
    renderLogs(payload.logs);
    renderSettings(payload.settings);
  } catch (error) {
    document.getElementById("overviewCards").innerHTML = `
      <article class="stats-card">
        <span class="stats-label">Error</span>
        <strong class="stats-value">No fue posible cargar el dashboard</strong>
      </article>
    `;
    console.error(error);
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Actualizar";
  }
}

function syncNavigation() {
  const currentHash = window.location.hash || "#overview";

  navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.getAttribute("href") === currentHash);
  });
}

refreshButton?.addEventListener("click", loadDashboard);
window.addEventListener("hashchange", syncNavigation);

syncNavigation();
loadDashboard();
