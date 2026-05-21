import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs/promises";
import path from "node:path";

const logsDir = path.resolve(__dirname, "../logging/logs");

const realtimePanelPath  = path.join(logsDir, "robot_controller_runs_realtime_panel.jsonl");
const localPlannerGridPath = path.join(logsDir, "local_planner_grid.jpg");
const cameraFeedPath     = path.join(logsDir, "camera_feed.jpg");
const simulationsPath    = path.join(logsDir, "simulations.jsonl");
const eventsPath         = path.join(logsDir, "events.jsonl");
const eventTelemetryPath = path.join(logsDir, "event_telemetry.jsonl");
const goalsConfigPath    = path.resolve(__dirname, "src/goals.config.json");
const readmePath         = path.resolve(__dirname, "../README.md");

type GoalPoint = {
  name: string;
  coordinates: [number, number];
};

type GoalsConfig = {
  Goals: GoalPoint[];
};

function isGoalPoint(value: unknown): value is GoalPoint {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const goal = value as { name?: unknown; coordinates?: unknown };
  return (
    typeof goal.name === "string" &&
    Array.isArray(goal.coordinates) &&
    goal.coordinates.length === 2 &&
    goal.coordinates.every((coordinate) => typeof coordinate === "number" && Number.isFinite(coordinate))
  );
}

function isGoalsConfig(value: unknown): value is GoalsConfig {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const config = value as { Goals?: unknown };
  return Array.isArray(config.Goals) && config.Goals.length > 0 && config.Goals.every(isGoalPoint);
}

function readRequestBody(req: NodeJS.ReadableStream): Promise<string> {
  return new Promise((resolve, reject) => {
    let body = "";
    req.setEncoding("utf-8");
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

async function writeGoalsConfig(config: GoalsConfig) {
  const tempPath = `${goalsConfigPath}.tmp`;
  await fs.writeFile(tempPath, `${JSON.stringify(config, null, 2)}\n`, "utf-8");
  await fs.rename(tempPath, goalsConfigPath);
}

async function serveJpeg(pathname: string, res: { statusCode: number; setHeader: (name: string, value: string) => void; end: (chunk?: string | Buffer) => void }) {
  try {
    const image = await fs.readFile(pathname);
    res.setHeader("Content-Type", "image/jpeg");
    res.setHeader("Cache-Control", "no-store");
    res.end(image);
  } catch {
    res.statusCode = 404;
    res.end("Image not found");
  }
}

async function serveJsonLines(pathname: string, res: { statusCode: number; setHeader: (name: string, value: string) => void; end: (chunk?: string) => void }) {
  try {
    const text = await fs.readFile(pathname, "utf-8");
    res.setHeader("Content-Type", "application/x-ndjson");
    res.setHeader("Cache-Control", "no-store");
    res.end(text);
  } catch {
    res.statusCode = 404;
    res.end("");
  }
}

async function serveText(pathname: string, res: { statusCode: number; setHeader: (name: string, value: string) => void; end: (chunk?: string) => void }) {
  try {
    const text = await fs.readFile(pathname, "utf-8");
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(text);
  } catch {
    res.statusCode = 404;
    res.end("");
  }
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: "agv-realtime-panel-api",
      configureServer(server) {
        server.middlewares.use("/api/realtime-panel", async (_req, res) => {
          try {
            const text = await fs.readFile(realtimePanelPath, "utf-8");
            const latestLine = text.trim().split(/\r?\n/).at(-1);

            res.setHeader("Content-Type", "application/json");
            res.end(latestLine ?? "{}");
          } catch {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: "No realtime panel data found" }));
          }
        });

        server.middlewares.use("/api/goals", async (req, res) => {
          if (req.method === "GET") {
            try {
              const text = await fs.readFile(goalsConfigPath, "utf-8");
              res.setHeader("Content-Type", "application/json");
              res.setHeader("Cache-Control", "no-store");
              res.end(text);
            } catch {
              res.statusCode = 404;
              res.end(JSON.stringify({ error: "No goals config found" }));
            }
            return;
          }

          if (req.method === "PUT") {
            try {
              const body = await readRequestBody(req);
              const config = JSON.parse(body);

              if (!isGoalsConfig(config)) {
                res.statusCode = 400;
                res.end(JSON.stringify({ error: "Invalid goals config" }));
                return;
              }

              await writeGoalsConfig(config);
              res.setHeader("Content-Type", "application/json");
              res.end(JSON.stringify(config));
            } catch {
              res.statusCode = 400;
              res.end(JSON.stringify({ error: "Could not save goals config" }));
            }
            return;
          }

          res.statusCode = 405;
          res.end(JSON.stringify({ error: "Method not allowed" }));
        });

        server.middlewares.use("/api/local-planner-grid", async (_req, res) => {
          await serveJpeg(localPlannerGridPath, res);
        });

        server.middlewares.use("/api/camera-feed", async (_req, res) => {
          await serveJpeg(cameraFeedPath, res);
        });

        server.middlewares.use("/api/simulations", async (_req, res) => {
          await serveJsonLines(simulationsPath, res);
        });

        server.middlewares.use("/api/events", async (_req, res) => {
          await serveJsonLines(eventsPath, res);
        });

        server.middlewares.use("/api/event-telemetry", async (_req, res) => {
          await serveJsonLines(eventTelemetryPath, res);
        });

        server.middlewares.use("/api/readme", async (_req, res) => {
          await serveText(readmePath, res);
        });
      },
    },
  ],
});
