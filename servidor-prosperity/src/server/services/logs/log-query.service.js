import fs from "fs";
import path from "path";
import { paths } from "../../config/paths.js";
import { listDirectories, listFiles, readJsonLines } from "../storage.js";

function listLogDateDirectories() {
  return listDirectories(paths.logs)
    .map((dirPath) => ({
      dirPath,
      name: path.basename(dirPath),
    }))
    .filter((item) => /^\d{4}-\d{2}-\d{2}$/.test(item.name))
    .sort((left, right) => right.name.localeCompare(left.name));
}

function listRecentSystemEvents(limit = 20) {
  const events = [];

  for (const entry of listLogDateDirectories()) {
    const filePath = path.join(entry.dirPath, "system.jsonl");

    if (!fs.existsSync(filePath)) {
      continue;
    }

    const lines = readJsonLines(filePath)
      .map((item) => ({
        ...item,
        source: "system",
        date_folder: entry.name,
      }))
      .reverse();

    events.push(...lines);

    if (events.length >= limit) {
      break;
    }
  }

  return events
    .sort((left, right) => String(right.timestamp_utc || "").localeCompare(String(left.timestamp_utc || "")))
    .slice(0, limit);
}

function listRecentErrorFiles(limit = 10) {
  return listFiles(paths.errors)
    .map((filePath) => ({
      filePath,
      name: path.basename(filePath),
      stats: fs.statSync(filePath),
    }))
    .sort((left, right) => right.stats.mtimeMs - left.stats.mtimeMs)
    .slice(0, limit)
    .map((item) => ({
      source: "error",
      file: item.name,
      timestamp: item.stats.mtime.toISOString(),
      size_bytes: item.stats.size,
    }));
}

export function buildLogsSnapshot() {
  const events = listRecentSystemEvents(20);
  const errors = listRecentErrorFiles(10);

  return {
    events,
    errors,
    total_events: events.length,
    total_errors: errors.length,
  };
}
