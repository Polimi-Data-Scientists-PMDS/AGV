import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs/promises";
import path from "node:path";

const realtimePanelPath = path.resolve(
  __dirname,
  "../logging/logs/robot_controller_runs_realtime_panel.jsonl",
);

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
      },
    },
  ],
});
