import net from "node:net";
import { spawn } from "node:child_process";

const port = Number(process.env.PORT || 3000);
const baseUrl = `http://localhost:${port}`;

function assertPortAvailable(targetPort) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", (error) => {
      if (error.code === "EADDRINUSE") {
        reject(new Error(`Puerto ${targetPort} no disponible. Cierra el proceso actual o usa PORT=otro_puerto.`));
        return;
      }
      reject(error);
    });
    server.once("listening", () => {
      server.close(() => resolve());
    });
    server.listen(targetPort, "0.0.0.0");
  });
}

await assertPortAvailable(port);

console.log("Iniciando MAGI demo backend...");
console.log(`URL base prevista: ${baseUrl}`);
console.log("Endpoints clave:");
console.log(`- POST ${baseUrl}/analisis`);
console.log(`- GET  ${baseUrl}/api/overview`);
console.log(`- GET  ${baseUrl}/api/snapshots`);

const child = spawn(process.execPath, ["src/server/index.js"], {
  stdio: "inherit",
  env: {
    ...process.env,
    PORT: String(port),
    DEMO_MODE: process.env.DEMO_MODE || "true",
  },
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
