import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type { IncomingMessage, ServerResponse } from "node:http";

const logsDir = path.resolve(__dirname, "../logging/logs");
const realtimeFilenamePattern = /^robot_controller_runs_(\d+)_realtime\.jsonl$/;
const emergencyStopPath = path.join(logsDir, "emergency_stop.flag");

const controllerGoalsConfigPath = path.resolve(
  __dirname,
  "../AGV_Webots_World_and_Controllers/controllers/DefaultController/goals.config.json",
);
const userGuidePath      = path.resolve(__dirname, "../docs/web-app-user-guide.md");
const loggingServerUrl   = process.env.LOGGING_SERVER_URL ?? "http://127.0.0.1:8080";

type GoalPoint = {
  name: string;
  coordinates: [number, number];
};

type ControllerGoalsConfig = {
  Goals: GoalPoint[];
  RobotRoutes: Record<string, string[]>;
};

type MoveGoalRequest = {
  unit_id: string;
  goal_index: number;
  direction: -1 | 1;
};

type CreateGoalRequest = {
  unit_id: string;
  name: string;
  coordinates: [number, number];
};

type RemoveGoalRequest = {
  unit_id: string;
  goal_index: number;
};

class GoalMoveRequestError extends Error {}
class GoalCreateRequestError extends Error {}
class GoalRemoveRequestError extends Error {}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isGoalPoint(value: unknown): value is GoalPoint {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const goal = value as { name?: unknown; coordinates?: unknown };
  return (
    typeof goal.name === "string" &&
    goal.name.length > 0 &&
    Array.isArray(goal.coordinates) &&
    goal.coordinates.length === 2 &&
    goal.coordinates.every(isFiniteNumber)
  );
}

function isControllerGoalsConfig(value: unknown): value is ControllerGoalsConfig {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const config = value as { Goals?: unknown; RobotRoutes?: unknown };
  if (
    !Array.isArray(config.Goals) ||
    config.Goals.length === 0 ||
    !config.Goals.every(isGoalPoint) ||
    typeof config.RobotRoutes !== "object" ||
    config.RobotRoutes === null ||
    Array.isArray(config.RobotRoutes)
  ) {
    return false;
  }

  const goalNames = new Set<string>();
  for (const goal of config.Goals) {
    if (goalNames.has(goal.name)) {
      return false;
    }
    goalNames.add(goal.name);
  }

  return Object.entries(config.RobotRoutes).every(([unitId, route]) => (
    /^\d+$/.test(unitId) &&
    Array.isArray(route) &&
    route.length > 0 &&
    route.every((goalName) => typeof goalName === "string" && goalNames.has(goalName))
  ));
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

function parseMoveGoalRequest(value: unknown): MoveGoalRequest {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new GoalMoveRequestError("Move request must be an object");
  }

  const request = value as Partial<MoveGoalRequest>;
  const unitId = request.unit_id;
  const goalIndex = request.goal_index;
  const direction = request.direction;
  if (typeof unitId !== "string" || !/^(0|[1-9]\d*)$/.test(unitId)) {
    throw new GoalMoveRequestError("unit_id must be a normalized numeric string");
  }
  if (typeof goalIndex !== "number" || !Number.isInteger(goalIndex) || goalIndex < 0) {
    throw new GoalMoveRequestError("goal_index must be a nonnegative integer");
  }
  if (direction !== -1 && direction !== 1) {
    throw new GoalMoveRequestError("direction must be -1 or 1");
  }

  return { unit_id: unitId, goal_index: goalIndex, direction };
}

function parseCreateGoalRequest(value: unknown): CreateGoalRequest {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new GoalCreateRequestError("Create request must be an object");
  }

  const request = value as Partial<CreateGoalRequest>;
  const unitId = request.unit_id;
  const name = request.name;
  const coordinates = request.coordinates;
  if (typeof unitId !== "string" || !/^(0|[1-9]\d*)$/.test(unitId)) {
    throw new GoalCreateRequestError("unit_id must be a normalized numeric string");
  }
  if (typeof name !== "string" || name.trim().length === 0) {
    throw new GoalCreateRequestError("name must be a nonempty string");
  }
  if (
    !Array.isArray(coordinates) ||
    coordinates.length !== 2 ||
    !coordinates.every(isFiniteNumber)
  ) {
    throw new GoalCreateRequestError("coordinates must contain exactly two finite numbers");
  }

  return { unit_id: unitId, name: name.trim(), coordinates: [coordinates[0], coordinates[1]] };
}

function parseRemoveGoalRequest(value: unknown): RemoveGoalRequest {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new GoalRemoveRequestError("Remove request must be an object");
  }

  const request = value as Partial<RemoveGoalRequest>;
  const unitId = request.unit_id;
  const goalIndex = request.goal_index;
  if (typeof unitId !== "string" || !/^(0|[1-9]\d*)$/.test(unitId)) {
    throw new GoalRemoveRequestError("unit_id must be a normalized numeric string");
  }
  if (typeof goalIndex !== "number" || !Number.isInteger(goalIndex) || goalIndex < 0) {
    throw new GoalRemoveRequestError("goal_index must be a nonnegative integer");
  }

  return { unit_id: unitId, goal_index: goalIndex };
}

async function readControllerGoalsConfig(): Promise<ControllerGoalsConfig> {
  let config: unknown;
  try {
    config = JSON.parse(await fs.readFile(controllerGoalsConfigPath, "utf-8"));
  } catch {
    throw new Error("Could not read the controller goals config");
  }

  if (!isControllerGoalsConfig(config)) {
    throw new Error("The controller goals config is invalid");
  }

  return config;
}

async function writeControllerGoalsConfig(config: ControllerGoalsConfig) {
  const tempPath = `${controllerGoalsConfigPath}.${randomUUID()}.tmp`;
  try {
    await fs.writeFile(tempPath, `${JSON.stringify(config, null, 2)}\n`, "utf-8");
    await fs.rename(tempPath, controllerGoalsConfigPath);
  } catch (error) {
    await fs.rm(tempPath, { force: true }).catch(() => undefined);
    throw error;
  }
}

async function readEmergencyStopState() {
  try {
    await fs.access(emergencyStopPath);
    return true;
  } catch (error) {
    if (hasErrorCode(error, "ENOENT")) {
      return false;
    }
    throw error;
  }
}

async function setEmergencyStopState(active: boolean) {
  if (!active) {
    await fs.rm(emergencyStopPath, { force: true });
    return;
  }

  await fs.mkdir(logsDir, { recursive: true });
  const temporaryPath = `${emergencyStopPath}.${randomUUID()}.tmp`;
  try {
    await fs.writeFile(temporaryPath, "active\n", "utf-8");
    await fs.rename(temporaryPath, emergencyStopPath);
  } catch (error) {
    await fs.rm(temporaryPath, { force: true }).catch(() => undefined);
    throw error;
  }
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

function sendJson(res: ServerResponse, statusCode: number, payload: object) {
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function hasErrorCode(error: unknown, code: string) {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as { code?: unknown }).code === code
  );
}

function normalizeNumericUnitId(unitId: string) {
  return unitId.replace(/^0+(?=\d)/, "");
}

function validateRealtimeUnitId(req: IncomingMessage, allowedQueryNames: readonly string[] = []) {
  const requestUrl = new URL(req.url ?? "/", "http://vite.local");
  const unknownNames = [...requestUrl.searchParams.keys()].filter(
    (name) => name !== "unit_id" && !allowedQueryNames.includes(name),
  );
  if (unknownNames.length > 0) {
    throw new Error(`Unknown query parameter(s): ${[...new Set(unknownNames)].sort().join(", ")}`);
  }

  const unitIds = requestUrl.searchParams.getAll("unit_id");
  if (unitIds.length !== 1 || !/^\d+$/.test(unitIds[0])) {
    throw new Error("unit_id must appear exactly once as a numeric string");
  }

  return normalizeNumericUnitId(unitIds[0]);
}

function validateNoQueryParameters(req: IncomingMessage) {
  const requestUrl = new URL(req.url ?? "/", "http://vite.local");
  if ([...requestUrl.searchParams.keys()].length > 0) {
    throw new Error("Query parameters are not allowed");
  }
}

function realtimePathForUnit(unitId: string) {
  return path.join(logsDir, `robot_controller_runs_${unitId}_realtime.jsonl`);
}

function imagePathForUnit(filenamePrefix: string, unitId: string) {
  return path.join(logsDir, `${filenamePrefix}_${unitId}.jpg`);
}

async function readRealtimeRecordAtPath(realtimePath: string, unitId: string) {
  let text: string;
  try {
    text = await fs.readFile(realtimePath, "utf-8");
  } catch (error) {
    if (hasErrorCode(error, "ENOENT")) {
      return { status: "missing" as const };
    }
    throw error;
  }

  const records = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (records.length === 0) {
    return { status: "missing" as const };
  }
  if (records.length !== 1) {
    return { status: "malformed" as const };
  }

  try {
    const payload: unknown = JSON.parse(records[0]);
    if (
      typeof payload !== "object" ||
      payload === null ||
      Array.isArray(payload) ||
      (payload as { unit_id?: unknown }).unit_id !== unitId
    ) {
      return { status: "malformed" as const };
    }
    return { status: "ok" as const, payload };
  } catch {
    return { status: "malformed" as const };
  }
}

async function readRealtimeRecord(unitId: string) {
  return readRealtimeRecordAtPath(realtimePathForUnit(unitId), unitId);
}

function compareNumericUnitIds(left: string, right: string) {
  if (left.length !== right.length) {
    return left.length - right.length;
  }
  return left.localeCompare(right);
}

async function discoverRealtimeUnitIds() {
  let entries;
  try {
    entries = await fs.readdir(logsDir, { withFileTypes: true });
  } catch (error) {
    if (hasErrorCode(error, "ENOENT")) {
      return [];
    }
    throw error;
  }

  const discoveredUnitIds = await Promise.all(
    entries.map(async (entry) => {
      if (!entry.isFile()) {
        return null;
      }

      const match = realtimeFilenamePattern.exec(entry.name);
      if (match === null) {
        return null;
      }

      const unitId = normalizeNumericUnitId(match[1]);
      try {
        const result = await readRealtimeRecordAtPath(path.join(logsDir, entry.name), unitId);
        return result.status === "ok" ? unitId : null;
      } catch {
        return null;
      }
    }),
  );

  return [...new Set(discoveredUnitIds.filter((unitId): unitId is string => unitId !== null))]
    .sort(compareNumericUnitIds);
}

async function proxyLoggingJson(endpoint: string, req: IncomingMessage, res: ServerResponse) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    sendJson(res, 405, { status: "error", message: "Method not allowed" });
    return;
  }

  try {
    const requestUrl = new URL(req.url ?? "/", "http://vite.local");
    const targetUrl = new URL(endpoint, loggingServerUrl);
    targetUrl.search = requestUrl.search;

    const response = await fetch(targetUrl, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const body = await response.text();

    res.statusCode = response.status;
    res.setHeader("Content-Type", response.headers.get("content-type") ?? "application/json");
    res.setHeader("Cache-Control", "no-store");
    res.end(body);
  } catch {
    sendJson(res, 502, { status: "error", message: "Logging service unavailable" });
  }
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: "agv-realtime-panel-api",
      configureServer(server) {
        server.middlewares.use("/api/realtime-units", async (req, res) => {
          if (req.method !== "GET") {
            res.setHeader("Allow", "GET");
            sendJson(res, 405, { status: "error", message: "Method not allowed" });
            return;
          }

          try {
            validateNoQueryParameters(req);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Invalid realtime-units query";
            sendJson(res, 400, { status: "error", message });
            return;
          }

          try {
            sendJson(res, 200, { unit_ids: await discoverRealtimeUnitIds() });
          } catch {
            sendJson(res, 500, {
              status: "error",
              message: "Could not discover realtime units",
            });
          }
        });

        server.middlewares.use("/api/realtime", async (req, res) => {
          if (req.method !== "GET") {
            res.setHeader("Allow", "GET");
            sendJson(res, 405, { status: "error", message: "Method not allowed" });
            return;
          }

          let unitId: string;
          try {
            unitId = validateRealtimeUnitId(req);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Invalid realtime query";
            sendJson(res, 400, { status: "error", message });
            return;
          }

          try {
            const result = await readRealtimeRecord(unitId);
            if (result.status === "missing") {
              sendJson(res, 404, {
                status: "error",
                message: `No realtime data found for unit ${unitId}`,
              });
              return;
            }
            if (result.status === "malformed") {
              sendJson(res, 500, {
                status: "error",
                message: `Realtime data for unit ${unitId} is malformed`,
              });
              return;
            }
            sendJson(res, 200, result.payload);
          } catch {
            sendJson(res, 500, {
              status: "error",
              message: `Could not read realtime data for unit ${unitId}`,
            });
          }
        });

        server.middlewares.use("/api/goals", async (req, res) => {
          if (req.method === "GET") {
            try {
              const text = await fs.readFile(controllerGoalsConfigPath, "utf-8");
              res.setHeader("Content-Type", "application/json");
              res.setHeader("Cache-Control", "no-store");
              res.end(text);
            } catch {
              res.statusCode = 404;
              res.end(JSON.stringify({ error: "No goals config found" }));
            }
            return;
          }

          if (req.method === "POST") {
            try {
              const body = await readRequestBody(req);
              const goal = parseCreateGoalRequest(JSON.parse(body));
              const config = await readControllerGoalsConfig();
              const route = config.RobotRoutes[goal.unit_id];
              if (route === undefined) {
                throw new GoalCreateRequestError(`No route is configured for unit ${goal.unit_id}`);
              }
              if (config.Goals.some((existingGoal) => existingGoal.name === goal.name)) {
                throw new GoalCreateRequestError(`Goal ${goal.name} already exists`);
              }

              const nextConfig: ControllerGoalsConfig = {
                ...config,
                Goals: [...config.Goals, { name: goal.name, coordinates: goal.coordinates }],
                RobotRoutes: { ...config.RobotRoutes, [goal.unit_id]: [...route, goal.name] },
              };
              if (!isControllerGoalsConfig(nextConfig)) {
                throw new Error("The updated controller goals config is invalid");
              }

              await writeControllerGoalsConfig(nextConfig);
              sendJson(res, 201, nextConfig);
            } catch (error) {
              if (error instanceof GoalCreateRequestError || error instanceof SyntaxError) {
                sendJson(res, 400, {
                  status: "error",
                  message: error instanceof Error ? error.message : "Invalid goal create request",
                });
                return;
              }

              sendJson(res, 500, { status: "error", message: "Could not update the controller goals config" });
            }
            return;
          }

          if (req.method === "DELETE") {
            try {
              const body = await readRequestBody(req);
              const removal = parseRemoveGoalRequest(JSON.parse(body));
              const config = await readControllerGoalsConfig();
              const route = config.RobotRoutes[removal.unit_id];
              if (route === undefined) {
                throw new GoalRemoveRequestError(`No route is configured for unit ${removal.unit_id}`);
              }
              if (route.length <= 1) {
                throw new GoalRemoveRequestError("The selected route must retain at least one goal");
              }
              if (removal.goal_index >= route.length) {
                throw new GoalRemoveRequestError("goal_index is outside the selected route");
              }

              const removedGoalName = route[removal.goal_index];
              const nextRoute = route.filter((_, index) => index !== removal.goal_index);
              const nextRoutes = { ...config.RobotRoutes, [removal.unit_id]: nextRoute };
              const stillReferenced = Object.values(nextRoutes).some((nextRobotRoute) => (
                nextRobotRoute.includes(removedGoalName)
              ));
              const nextConfig: ControllerGoalsConfig = {
                ...config,
                Goals: stillReferenced
                  ? config.Goals
                  : config.Goals.filter((goal) => goal.name !== removedGoalName),
                RobotRoutes: nextRoutes,
              };
              if (!isControllerGoalsConfig(nextConfig)) {
                throw new Error("The updated controller goals config is invalid");
              }

              await writeControllerGoalsConfig(nextConfig);
              sendJson(res, 200, nextConfig);
            } catch (error) {
              if (error instanceof GoalRemoveRequestError || error instanceof SyntaxError) {
                sendJson(res, 400, {
                  status: "error",
                  message: error instanceof Error ? error.message : "Invalid goal remove request",
                });
                return;
              }

              sendJson(res, 500, { status: "error", message: "Could not update the controller goals config" });
            }
            return;
          }

          if (req.method === "PUT") {
            try {
              const body = await readRequestBody(req);
              const move = parseMoveGoalRequest(JSON.parse(body));
              const config = await readControllerGoalsConfig();
              const route = config.RobotRoutes[move.unit_id];
              if (route === undefined) {
                throw new GoalMoveRequestError(`No route is configured for unit ${move.unit_id}`);
              }

              const nextIndex = move.goal_index + move.direction;
              if (nextIndex < 0 || nextIndex >= route.length) {
                throw new GoalMoveRequestError("Goal cannot be moved in the requested direction");
              }

              const nextRoute = [...route];
              [nextRoute[move.goal_index], nextRoute[nextIndex]] = [nextRoute[nextIndex], nextRoute[move.goal_index]];
              const nextConfig: ControllerGoalsConfig = {
                ...config,
                RobotRoutes: { ...config.RobotRoutes, [move.unit_id]: nextRoute },
              };

              if (!isControllerGoalsConfig(nextConfig)) {
                throw new Error("The updated controller goals config is invalid");
              }

              await writeControllerGoalsConfig(nextConfig);
              sendJson(res, 200, nextConfig);
            } catch (error) {
              if (error instanceof GoalMoveRequestError || error instanceof SyntaxError) {
                sendJson(res, 400, {
                  status: "error",
                  message: error instanceof Error ? error.message : "Invalid goal move request",
                });
                return;
              }

              sendJson(res, 500, { status: "error", message: "Could not update the controller goals config" });
            }
            return;
          }

          res.setHeader("Allow", "GET, POST, PUT, DELETE");
          sendJson(res, 405, { status: "error", message: "Method not allowed" });
        });

        server.middlewares.use("/api/emergency-stop", async (req, res) => {
          try {
            validateNoQueryParameters(req);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Could not update emergency stop state";
            sendJson(res, 400, { status: "error", message });
            return;
          }

          try {
            if (req.method === "GET") {
              sendJson(res, 200, { active: await readEmergencyStopState() });
              return;
            }
            if (req.method === "POST") {
              await setEmergencyStopState(true);
              sendJson(res, 200, { active: true });
              return;
            }
            if (req.method === "DELETE") {
              await setEmergencyStopState(false);
              sendJson(res, 200, { active: false });
              return;
            }

            res.setHeader("Allow", "GET, POST, DELETE");
            sendJson(res, 405, { status: "error", message: "Method not allowed" });
          } catch (error) {
            const message = error instanceof Error ? error.message : "Could not update emergency stop state";
            sendJson(res, 500, { status: "error", message });
          }
        });

        server.middlewares.use("/api/local-planner-grid", async (req, res) => {
          if (req.method !== "GET") {
            res.setHeader("Allow", "GET");
            sendJson(res, 405, { status: "error", message: "Method not allowed" });
            return;
          }

          try {
            const unitId = validateRealtimeUnitId(req, ["t"]);
            await serveJpeg(imagePathForUnit("local_planner_grid", unitId), res);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Invalid local planner grid query";
            sendJson(res, 400, { status: "error", message });
          }
        });

        server.middlewares.use("/api/camera-feed", async (req, res) => {
          if (req.method !== "GET") {
            res.setHeader("Allow", "GET");
            sendJson(res, 405, { status: "error", message: "Method not allowed" });
            return;
          }

          try {
            const unitId = validateRealtimeUnitId(req, ["t"]);
            await serveJpeg(imagePathForUnit("camera_feed", unitId), res);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Invalid camera feed query";
            sendJson(res, 400, { status: "error", message });
          }
        });

        server.middlewares.use("/api/database-snapshot", async (req, res) => {
          await proxyLoggingJson("/database-snapshot", req, res);
        });

        server.middlewares.use("/api/simulation-options", async (req, res) => {
          await proxyLoggingJson("/simulation-options", req, res);
        });

        server.middlewares.use("/api/help-guide", async (_req, res) => {
          await serveText(userGuidePath, res);
        });
      },
    },
  ],
});
