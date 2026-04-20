import { botAConnector } from "./adapters/bot-a.js";
import { botBConnector } from "./adapters/bot-b.js";
import { botCConnector } from "./adapters/bot-c.js";
import { melchorConnector } from "./adapters/melchor.js";
import { baltasarConnector } from "./adapters/baltasar.js";
import { gasparConnector } from "./adapters/gaspar.js";
import { ceoMagiConnector } from "./adapters/ceo-magi.js";
import { buildConnectorSnapshot } from "./shared.js";

export const connectorRegistry = [
  botAConnector,
  botBConnector,
  botCConnector,
  melchorConnector,
  baltasarConnector,
  gasparConnector,
  ceoMagiConnector,
];

export function listConnectors() {
  return connectorRegistry.map(buildConnectorSnapshot);
}

export function listConnectorNames() {
  return connectorRegistry.map((connector) => connector.name);
}

export function getConnectorById(id) {
  const connector = connectorRegistry.find((item) => item.id === id);
  return connector ? buildConnectorSnapshot(connector) : null;
}
