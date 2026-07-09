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

export const emptySimulationTableData: SimulationTableData = {
  simulations: [],
  events: [],
  telemetry: [],
};

export const simulationColumns: Column[] = [
  { key: "id", label: "Sim ID" },
  { key: "controller_version", label: "Controller" },
  { key: "total_sim_time", label: "Total Time" },
  { key: "total_idle_time", label: "Idle Time" },
  { key: "obstacle_count", label: "Obstacles" },
  { key: "event_count", label: "Events" },
];

export const eventColumns: Column[] = [
  { key: "sim_id", label: "Sim ID" },
  { key: "sim_time", label: "Sim Time" },
  { key: "e_type", label: "Type" },
  { key: "details", label: "Details" },
];

export const telemetryColumns: Column[] = [
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

export const parseJsonLines = (text: string): TableRow[] =>
  text
    .replace(/}\s*{/g, "}\n{")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as TableRow);

export const fetchJsonLines = async (url: string): Promise<TableRow[]> => {
  const response = await fetch(url);
  return response.ok ? parseJsonLines(await response.text()) : [];
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

export async function fetchSimulationTableData(): Promise<SimulationTableData> {
  const [simulationRows, events, telemetry] = await Promise.all([
    fetchJsonLines("/api/simulations"),
    fetchJsonLines("/api/events"),
    fetchJsonLines("/api/event-telemetry"),
  ]);

  return {
    simulations: latestSimulationRows(simulationRows),
    events,
    telemetry,
  };
}
