import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..", "..", "..");
const repoRoot = path.resolve(projectRoot, "..");

export const paths = {
  root: projectRoot,
  repoRoot,
  config: path.join(repoRoot, "config"),
  client: path.join(projectRoot, "src", "client"),
  clientAssets: path.join(projectRoot, "src", "client", "assets"),
  data: path.join(projectRoot, "data"),
  analysis: path.join(projectRoot, "data", "analysis"),
  errors: path.join(projectRoot, "data", "errors"),
  logs: path.join(projectRoot, "data", "logs"),
  responses: path.join(projectRoot, "data", "responses"),
  snapshots: path.join(projectRoot, "data", "snapshots"),
  snapshotLegacy: path.join(projectRoot, "data", "snapshots", "legacy"),
  snapshotNormalized: path.join(projectRoot, "data", "snapshots", "normalized"),
  votes: path.join(projectRoot, "data", "votes"),
  melchorVotes: path.join(projectRoot, "data", "votes", "melchor"),
  execution: path.join(projectRoot, "data", "execution"),
  system: path.join(projectRoot, "data", "system"),
  training: path.join(projectRoot, "data", "training"),
  docs: path.join(projectRoot, "docs"),
  integrations: path.join(projectRoot, "integrations"),
};

export function resolveFromRoot(...segments) {
  return path.join(projectRoot, ...segments);
}
