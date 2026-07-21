import type { RobotData } from "./types";

export type TableValue = string | number | boolean | null | undefined;
export type TableRow = Record<string, TableValue>;

export type Column = {
  key: string;
  label: string;
};

export type SimulationTableData = {
  simulations: TableRow[];
  events: TableRow[];
  telemetry: TableRow[];
};

export type SimulationDataFilters = {
  unitId?: string;
  simId?: number;
};

export type SimulationOption = {
  unitId: string;
  simIds: number[];
};

export const DATABASE_REFRESH_OPTIONS_MS = [3_000, 5_000, 10_000, 15_000, 30_000] as const;
export type DatabaseRefreshMs = (typeof DATABASE_REFRESH_OPTIONS_MS)[number];

export const DEFAULT_DATABASE_REFRESH_MS: DatabaseRefreshMs = 10_000;

export const isDatabaseRefreshMs = (value: number): value is DatabaseRefreshMs =>
  DATABASE_REFRESH_OPTIONS_MS.some((option) => option === value);

export const LIVE_REFRESH_OPTIONS_MS = [50, 100, 250, 500, 1_000] as const;
export type LiveRefreshMs = (typeof LIVE_REFRESH_OPTIONS_MS)[number];

export const DEFAULT_LIVE_REFRESH_MS: LiveRefreshMs = 50;

export const isLiveRefreshMs = (value: number): value is LiveRefreshMs =>
  LIVE_REFRESH_OPTIONS_MS.some((option) => option === value);

export const emptySimulationTableData: SimulationTableData = {
  simulations: [],
  events: [],
  telemetry: [],
};

export const simulationColumns: Column[] = [
  { key: "id", label: "Sim ID" },
  { key: "unit_id", label: "Unit ID" },
  { key: "total_sim_time", label: "Total Time" },
  { key: "total_idle_time", label: "Idle Time" },
  { key: "obstacle_count", label: "Obstacles" },
  { key: "event_count", label: "Events" },
];

export const eventColumns: Column[] = [
  { key: "unit_id", label: "Unit ID" },
  { key: "sim_id", label: "Sim ID" },
  { key: "sim_time", label: "Sim Time" },
  { key: "e_type", label: "Type" },
  { key: "details", label: "Details" },
];

export const telemetryColumns: Column[] = [
  { key: "unit_id", label: "Unit ID" },
  { key: "sim_id", label: "Sim ID" },
  { key: "event_time", label: "Event Time" },
  { key: "e_type", label: "Type" },
  { key: "state_x", label: "State X" },
  { key: "state_y", label: "State Y" },
  { key: "state_theta", label: "State Theta" },
  { key: "gps_x", label: "GPS X" },
  { key: "gps_y", label: "GPS Y" },
  { key: "error_distance", label: "Error Distance" },
  { key: "error_heading", label: "Error Heading" },
  { key: "current_vel_linear", label: "Current Linear" },
  { key: "current_vel_angular", label: "Current Angular" },
  { key: "target_vel_linear", label: "Target Linear" },
  { key: "target_vel_angular", label: "Target Angular" },
  { key: "next_point_x", label: "Next Point X" },
  { key: "next_point_y", label: "Next Point Y" },
];

export const formatTableValue = (value: TableValue) => value ?? "";

export const asNumber = (value: TableValue) => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue : null;
  }

  return null;
};

export const isNumericValue = (value: TableValue) => asNumber(value) !== null;

export const isUnitId = (value: unknown): value is string =>
  typeof value === "string" && /^(0|[1-9]\d*)$/.test(value);

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

const hasFiniteFields = <Field extends string>(
  value: unknown,
  fields: readonly Field[],
): value is Record<Field, number> => {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return fields.every((field) => isFiniteNumber(record[field]));
};

const isRobotData = (value: unknown): value is RobotData => {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const data = value as Partial<Record<keyof RobotData, unknown>>;
  return (
    isUnitId(data.unit_id) &&
    Number.isInteger(data.sim_id) &&
    isFiniteNumber(data.sim_id) &&
    data.sim_id > 0 &&
    isFiniteNumber(data.time) &&
    data.time >= 0 &&
    hasFiniteFields(data.state, ["x", "y", "theta"]) &&
    hasFiniteFields(data.gps, ["x", "y"]) &&
    hasFiniteFields(data.errors, ["distance", "heading"]) &&
    hasFiniteFields(data.current_velocities, ["linear", "angular"]) &&
    hasFiniteFields(data.target_velocities, ["linear", "angular"]) &&
    hasFiniteFields(data.goal_position, ["x", "y"]) &&
    (data.next_point === null || hasFiniteFields(data.next_point, ["x", "y"]))
  );
};

const isRealtimeUnitsResponse = (value: unknown): value is { unit_ids: string[] } => {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const unitIds = (value as { unit_ids?: unknown }).unit_ids;
  return (
    Array.isArray(unitIds) &&
    unitIds.every(isUnitId) &&
    new Set(unitIds).size === unitIds.length
  );
};

const isPositiveInteger = (value: unknown): value is number =>
  Number.isInteger(value) && isFiniteNumber(value) && value > 0;

const isNewestFirstSimulationIds = (simIds: unknown): simIds is number[] =>
  Array.isArray(simIds) &&
  simIds.every(isPositiveInteger) &&
  simIds.every((simId, index) => index === 0 || simId < simIds[index - 1]);

const isSimulationOptionsResponse = (
  value: unknown,
): value is { units: Array<{ unit_id: string; sim_ids: number[] }> } => {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const units = (value as { units?: unknown }).units;
  if (!Array.isArray(units)) {
    return false;
  }

  const unitIds = new Set<string>();
  return units.every((unit) => {
    if (typeof unit !== "object" || unit === null || Array.isArray(unit)) {
      return false;
    }

    const option = unit as { unit_id?: unknown; sim_ids?: unknown };
    if (!isUnitId(option.unit_id) || !isNewestFirstSimulationIds(option.sim_ids)) {
      return false;
    }
    if (unitIds.has(option.unit_id)) {
      return false;
    }
    unitIds.add(option.unit_id);
    return true;
  });
};

const simulationId = (row: TableRow) => row.id ?? row.sim_id;

export const latestSimulationRows = (rows: TableRow[]) => {
  const latest = new Map<TableValue, TableRow>();
  const withoutId: TableRow[] = [];

  rows.forEach((row) => {
    const id = simulationId(row);
    if (id === null || id === undefined) {
      withoutId.push(row);
    } else {
      latest.set(id, row);
    }
  });

  return [...latest.values(), ...withoutId];
};

const isTableRowArray = (value: unknown): value is TableRow[] =>
  Array.isArray(value) &&
  value.every((row) => typeof row === "object" && row !== null && !Array.isArray(row));

const isSimulationTableData = (value: unknown): value is SimulationTableData => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const snapshot = value as Partial<Record<keyof SimulationTableData, unknown>>;
  return (
    isTableRowArray(snapshot.simulations) &&
    isTableRowArray(snapshot.events) &&
    isTableRowArray(snapshot.telemetry)
  );
};

const databaseSnapshotUrl = ({ unitId, simId }: SimulationDataFilters) => {
  const query = new URLSearchParams();
  if (unitId !== undefined) {
    query.set("unit_id", unitId);
  }
  if (simId !== undefined) {
    query.set("sim_id", String(simId));
  }
  const queryString = query.toString();
  return `/api/database-snapshot${queryString ? `?${queryString}` : ""}`;
};

export async function fetchSimulationTableData(
  request: SimulationDataFilters = {},
): Promise<SimulationTableData> {
  const response = await fetch(databaseSnapshotUrl(request), {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Database snapshot request failed with status ${response.status}.`);
  }

  const snapshot: unknown = await response.json();
  if (!isSimulationTableData(snapshot)) {
    throw new Error("Database snapshot response is malformed.");
  }

  return {
    simulations: latestSimulationRows(snapshot.simulations),
    events: snapshot.events,
    telemetry: snapshot.telemetry,
  };
}

export async function fetchSimulationOptions(): Promise<SimulationOption[]> {
  const response = await fetch("/api/simulation-options", {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Simulation option request failed with status ${response.status}.`);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error("Simulation option response is malformed.");
  }
  if (!isSimulationOptionsResponse(payload)) {
    throw new Error("Simulation option response is malformed.");
  }

  return payload.units.map(({ unit_id: unitId, sim_ids: simIds }) => ({ unitId, simIds }));
}

export async function fetchRealtimeUnitIds(): Promise<string[]> {
  const response = await fetch("/api/realtime-units", {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Realtime unit discovery failed with status ${response.status}.`);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error("Realtime unit discovery response is malformed.");
  }
  if (!isRealtimeUnitsResponse(payload)) {
    throw new Error("Realtime unit discovery response is malformed.");
  }

  return payload.unit_ids;
}

export async function fetchRobotData(unitId: string): Promise<RobotData> {
  if (!isUnitId(unitId)) {
    throw new Error("Realtime unit_id must be a normalized numeric string.");
  }

  const query = new URLSearchParams({ unit_id: unitId });
  const response = await fetch(`/api/realtime?${query.toString()}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Realtime data request failed with status ${response.status}.`);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error("Realtime data response is malformed.");
  }
  if (!isRobotData(payload) || payload.unit_id !== unitId) {
    throw new Error("Realtime data response is malformed or belongs to another unit.");
  }

  return payload;
}
