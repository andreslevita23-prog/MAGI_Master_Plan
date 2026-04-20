const moduleCards = [
  {
    id: "melchor",
    name: "Melchor",
    role: "Seguridad / Riesgo",
    status: "healthy",
    summary: "Politicas y limites listos para futura conexion de riesgo.",
  },
  {
    id: "baltasar",
    name: "Baltasar",
    role: "Analisis tecnico / Datos",
    status: "warning",
    summary: "Esperando fuentes reales para poblar indicadores y series.",
  },
  {
    id: "gaspar",
    name: "Gaspar",
    role: "Exploracion / Oportunidad",
    status: "pending",
    summary: "Watchlists y filtros quedaran conectados en una fase posterior.",
  },
  {
    id: "ceo-magi",
    name: "CEO-MAGI",
    role: "Decision final",
    status: "offline",
    summary: "Reservado como capa visual hasta definir criterio de orquestacion.",
  },
];

const recentActivityMock = [
  {
    id: "evt-01",
    timestamp: "2026-04-19T07:45:00Z",
    title: "Dashboard base actualizado",
    detail: "Se publico una vista limpia con placeholders para metricas y modulos.",
    type: "ui",
  },
  {
    id: "evt-02",
    timestamp: "2026-04-19T07:20:00Z",
    title: "Conexiones en modo placeholder",
    detail: "Bot A, Bot B y Bot C permanecen definidos solo como referencias visuales.",
    type: "connection",
  },
  {
    id: "evt-03",
    timestamp: "2026-04-19T06:55:00Z",
    title: "Health local verificado",
    detail: "La app responde en local y el dashboard se alimenta desde un endpoint minimo.",
    type: "system",
  },
  {
    id: "evt-04",
    timestamp: "2026-04-19T06:10:00Z",
    title: "Matriz MAGI preparada",
    detail: "Los estados de Melchor, Baltasar, Gaspar y CEO-MAGI quedaron listos para reemplazar mocks.",
    type: "module",
  },
];

function buildOverview(uptimeSeconds) {
  const now = new Date().toISOString();

  return {
    status: "Operational",
    uptimeLabel: `${Math.max(4, Math.floor(uptimeSeconds / 3600) || 4)}h 18m`,
    lastUpdated: now,
    summary:
      "Panel visual base activo. La interfaz ya esta lista para recibir metricas reales sin rehacer la estructura.",
  };
}

function buildMetrics() {
  return [
    {
      id: "total-signals",
      label: "Total signals",
      value: "128",
      helper: "Placeholder mensual",
      tone: "neutral",
    },
    {
      id: "win-rate",
      label: "Win rate",
      value: "61.4%",
      helper: "Mock referencial",
      tone: "positive",
    },
    {
      id: "active-modules",
      label: "Active modules",
      value: "2 / 4",
      helper: "Melchor y Baltasar visibles",
      tone: "neutral",
    },
    {
      id: "system-health",
      label: "System health",
      value: "92%",
      helper: "Estado general placeholder",
      tone: "positive",
    },
    {
      id: "trades-today",
      label: "Trades today",
      value: "06",
      helper: "No conectado a trading real",
      tone: "neutral",
    },
    {
      id: "alerts",
      label: "Alerts",
      value: "03",
      helper: "Eventos simulados de supervision",
      tone: "warning",
    },
  ];
}

function buildSettingsSnapshot(port, hasOpenAIKey) {
  return {
    environment: process.env.NODE_ENV || "development",
    domain: process.env.MAGI_SITE_URL || "https://prosperity.lat",
    localUrl: `http://localhost:${port}`,
    placeholders: [
      {
        key: "Bot A",
        value: process.env.MAGI_BOT_A_ENDPOINT || "pending",
        status: "placeholder",
      },
      {
        key: "Bot B",
        value: process.env.MAGI_BOT_B_ENDPOINT || "pending",
        status: "placeholder",
      },
      {
        key: "Bot C",
        value: process.env.MAGI_BOT_C_ENDPOINT || "pending",
        status: "placeholder",
      },
      {
        key: "OpenAI",
        value: hasOpenAIKey ? "configured" : "not configured",
        status: hasOpenAIKey ? "ready" : "placeholder",
      },
      {
        key: "API",
        value: `/api/dashboard`,
        status: "ready",
      },
      {
        key: "Environment",
        value: process.env.NODE_ENV || "development",
        status: "ready",
      },
    ],
  };
}

export function buildDashboardSnapshot({ uptimeSeconds, port, hasOpenAIKey }) {
  return {
    overview: buildOverview(uptimeSeconds),
    metrics: buildMetrics(),
    modules: moduleCards,
    recentActivity: recentActivityMock,
    settings: buildSettingsSnapshot(port, hasOpenAIKey),
    signals: [],
    logs: [],
  };
}
