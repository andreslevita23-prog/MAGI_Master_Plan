import { spawn } from "child_process";

const server = spawn("node", ["src/server/index.js"], {
  stdio: "ignore",
});

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

try {
  await wait(2000);

  const health = await fetch("http://localhost:3000/health").then((res) => res.json());
  const dashboard = await fetch("http://localhost:3000/api/dashboard").then((res) => res.json());
  const connectors = await fetch("http://localhost:3000/api/connectors").then((res) =>
    res.json(),
  );

  console.log(
    JSON.stringify(
      {
        health,
        overview: dashboard.overview,
        modules: dashboard.modules.length,
        connectors: connectors.length,
      },
      null,
      2,
    ),
  );
} finally {
  server.kill();
}
