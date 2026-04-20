import fs from "fs";
import path from "path";
import { paths } from "../config/paths.js";

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function getUtcDateString(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function appendJsonLine(fileName, payload) {
  const now = new Date();
  const datedFolder = path.join(paths.logs, getUtcDateString(now));
  ensureDir(datedFolder);

  const entry = {
    timestamp_utc: now.toISOString(),
    timestamp_local: now.toLocaleString("es-CO"),
    ...payload,
  };

  fs.appendFileSync(
    path.join(datedFolder, fileName),
    `${JSON.stringify(entry)}\n`,
    "utf8",
  );
}

export const logger = {
  logBotA(data) {
    appendJsonLine("botA.jsonl", data);
  },
  logAPI(data) {
    appendJsonLine("api.jsonl", data);
  },
  logBotB(data) {
    appendJsonLine("botB.jsonl", data);
  },
  logSystem(data) {
    appendJsonLine("system.jsonl", data);
  },
};
