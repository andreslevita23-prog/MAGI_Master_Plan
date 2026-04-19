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
  document.getElementById("overviewHero").innerHTML = `
    <article class="overview-panel">
      <div class="overview-copy">
        <span class="stats-label">System status</span>
        <strong class="overview-status">${overview.status}</strong>
        <p class="muted">${overview.summary}</p>
      </div>
      <div class="overview-meta">
        <div class="overview-item">
          <span class="stats-label">Uptime</span>
          <strong>${overview.uptimeLabel}</strong>
        </div>
        <div class="overview-item">
          <span class="stats-label">Last update</span>
          <strong>${formatDate(overview.lastUpdated)}</strong>
        </div>
      </div>
    </article>
  `;
}

function metricToneClass(tone) {
  return `metric-${tone || "neutral"}`;
}

function renderMetrics(metrics) {
  document.getElementById("metricsGrid").innerHTML = metrics
    .map(
      (metric) => `
        <article class="stats-card ${metricToneClass(metric.tone)}">
          <span class="stats-label">${metric.label}</span>
          <strong class="stats-value">${metric.value}</strong>
          <p class="muted">${metric.helper}</p>
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
          <p class="muted">${module.summary}</p>
          <span class="module-status module-status-${module.status}">${module.status}</span>
        </article>
      `,
    )
    .join("");
}

function activityTypeClass(type) {
  return `activity-${type || "system"}`;
}

function renderActivity(items) {
  const node = document.getElementById("activityFeed");

  node.innerHTML = items
    .map(
      (item) => `
        <article class="activity-entry">
          <div class="activity-head">
            <span class="badge ${activityTypeClass(item.type)}">${item.type}</span>
            <span class="mono muted">${formatDate(item.timestamp)}</span>
          </div>
          <strong>${item.title}</strong>
          <p>${item.detail}</p>
        </article>
      `,
    )
    .join("");
}

function renderSettings(settings) {
  const cards = [
    {
      key: "Environment",
      body: `<strong>${settings.environment}</strong><p class="muted">Dominio previsto: ${settings.domain}</p><p class="muted">Local: ${settings.localUrl}</p>`,
    },
    {
      key: "Connectivity",
      body: `<ul>${settings.placeholders
        .map((item) => `<li><strong>${item.key}:</strong> ${item.value}</li>`)
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
    renderMetrics(payload.metrics);
    renderModules(payload.modules);
    renderActivity(payload.recentActivity);
    renderSettings(payload.settings);
  } catch (error) {
    document.getElementById("overviewHero").innerHTML = `
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
