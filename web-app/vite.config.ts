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
      },
    },
  ],
});
