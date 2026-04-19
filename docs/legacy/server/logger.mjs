// logger.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Crea carpeta de logs por fecha UTC si no existe
function ensureLogFolder(date) {
  const folder = path.join(__dirname, 'logs', date);
  if (!fs.existsSync(folder)) {
    fs.mkdirSync(folder, { recursive: true });
  }
  return folder;
}

function getUTCDateString(dateObj) {
  return dateObj.toISOString().slice(0, 10); // YYYY-MM-DD
}

function logToFile(filename, data) {
  const now = new Date();
  const date = getUTCDateString(now);
  const folder = ensureLogFolder(date);
  const fullPath = path.join(folder, filename);

  const logEntry = {
    timestamp_utc: now.toISOString(),
    timestamp_local: now.toLocaleString(),
    ...data,
  };

  fs.appendFileSync(fullPath, JSON.stringify(logEntry) + '\n');
  console.log(`📥 Log guardado en ${filename} (${date})`);
}

export default {
  logBotA: (data) => logToFile('botA.jsonl', data),
  logAPI: (data) => logToFile('api.jsonl', data),
  logBotB: (data) => logToFile('botB.jsonl', data),
};
