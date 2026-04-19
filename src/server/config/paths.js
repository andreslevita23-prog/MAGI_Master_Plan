import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..", "..", "..");

export const paths = {
  root: projectRoot,
  client: path.join(projectRoot, "src", "client"),
  clientAssets: path.join(projectRoot, "src", "client", "assets"),
  data: path.join(projectRoot, "data"),
  analysis: path.join(projectRoot, "data", "analysis"),
  errors: path.join(projectRoot, "data", "errors"),
  logs: path.join(projectRoot, "data", "logs"),
  responses: path.join(projectRoot, "data", "responses"),
  training: path.join(projectRoot, "data", "training"),
  docs: path.join(projectRoot, "docs"),
  integrations: path.join(projectRoot, "integrations"),
};

export function resolveFromRoot(...segments) {
  return path.join(projectRoot, ...segments);
}
