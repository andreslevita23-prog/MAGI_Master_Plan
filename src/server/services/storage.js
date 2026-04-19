import fs from "fs";
import path from "path";
import { paths } from "../config/paths.js";

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

export function ensureProjectDirectories() {
  Object.values(paths)
    .filter((value) => typeof value === "string")
    .forEach((dirPath) => {
      if (
        dirPath.includes(`${path.sep}data`) ||
        dirPath.includes(`${path.sep}docs`) ||
        dirPath.includes(`${path.sep}integrations`)
      ) {
        ensureDir(dirPath);
      }
    });
}

export function readJson(filePath, fallback = null) {
  try {
    if (!fs.existsSync(filePath)) {
      return fallback;
    }
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

export function writeJson(filePath, value) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2), "utf8");
}

export function appendText(filePath, content) {
  ensureDir(path.dirname(filePath));
  fs.appendFileSync(filePath, content, "utf8");
}

export function readJsonLines(filePath) {
  if (!fs.existsSync(filePath)) {
    return [];
  }

  return fs
    .readFileSync(filePath, "utf8")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

export function listFiles(dirPath, extension = "") {
  if (!fs.existsSync(dirPath)) {
    return [];
  }

  return fs
    .readdirSync(dirPath)
    .filter((entry) => !extension || entry.endsWith(extension))
    .map((entry) => path.join(dirPath, entry));
}

export function listDirectories(dirPath) {
  if (!fs.existsSync(dirPath)) {
    return [];
  }

  return fs
    .readdirSync(dirPath, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(dirPath, entry.name));
}
