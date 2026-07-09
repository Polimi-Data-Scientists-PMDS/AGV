import { useEffect, useMemo, useState } from "react";
import {
  asNumber,
  emptySimulationTableData,
  eventColumns,
  fetchSimulationTableData,
  formatTableValue,
  isNumericValue,
  simulationColumns,
  telemetryColumns,
  type Column,
  type SimulationTableData,
  type TableRow,
} from "./data";

type DataTableProps = {
  title: string;
  emptyMessage: string;
  columns: Column[];
  rows: TableRow[];
  defaultOpen?: boolean;
  compact?: boolean;
};

type SimulationTablesProps = {
  data: SimulationTableData;
  defaultOpen?: boolean;
  compact?: boolean;
};

const allEventTypes = "__ALL_EVENT_TYPES__";
const allSimulationIds = "__ALL_SIMULATION_IDS__";

function simulationIdOf(row: TableRow) {
  const rawId = row.id ?? row.sim_id;
  if (rawId === null || rawId === undefined) {
    return "";
  }

  return String(rawId).trim();
}

function eventTypeOf(row: TableRow) {
  const rawType = row.e_type ?? row.event_type;
  if (rawType === null || rawType === undefined) {
    return "";
  }

  return String(rawType).trim();
}

function buildEventTypeOptions(data: SimulationTableData) {
  const eventCounts = new Map<string, number>();
  const telemetryCounts = new Map<string, number>();

  data.events.forEach((row) => {
    const type = eventTypeOf(row);
    if (type) {
      eventCounts.set(type, (eventCounts.get(type) ?? 0) + 1);
    }
  });

  data.telemetry.forEach((row) => {
    const type = eventTypeOf(row);
    if (type) {
      telemetryCounts.set(type, (telemetryCounts.get(type) ?? 0) + 1);
    }
  });

  return Array.from(new Set([...eventCounts.keys(), ...telemetryCounts.keys()]))
    .sort((a, b) => a.localeCompare(b))
    .map((type) => ({
      type,
      count: eventCounts.get(type) ?? telemetryCounts.get(type) ?? 0,
    }));
}

function buildSimulationOptions(data: SimulationTableData) {
  const counts = new Map<string, { events: number; telemetry: number; simulations: number }>();

  function ensure(id: string) {
    const current = counts.get(id) ?? { events: 0, telemetry: 0, simulations: 0 };
    counts.set(id, current);
    return current;
  }

  data.simulations.forEach((row) => {
    const id = simulationIdOf(row);
    if (id) {
      ensure(id).simulations += 1;
    }
  });

  data.events.forEach((row) => {
    const id = simulationIdOf(row);
    if (id) {
      ensure(id).events += 1;
    }
  });

  data.telemetry.forEach((row) => {
    const id = simulationIdOf(row);
    if (id) {
      ensure(id).telemetry += 1;
    }
  });

  return Array.from(counts.entries())
    .sort(([a], [b]) => {
      const numericA = Number(a);
      const numericB = Number(b);
      if (Number.isFinite(numericA) && Number.isFinite(numericB)) {
        return numericB - numericA;
      }

      return a.localeCompare(b);
    })
    .map(([id, count]) => ({
      id,
      count: count.events || count.telemetry || count.simulations,
    }));
}

function filterRowsBySimulationId(rows: TableRow[], selectedSimulationId: string) {
  if (selectedSimulationId === allSimulationIds) {
    return rows;
  }

  return rows.filter((row) => simulationIdOf(row) === selectedSimulationId);
}

function filterRowsByEventType(rows: TableRow[], selectedEventType: string) {
  if (selectedEventType === allEventTypes) {
    return rows;
  }

  return rows.filter((row) => eventTypeOf(row) === selectedEventType);
}

export function DataTable({ title, emptyMessage, columns, rows, defaultOpen = false, compact = false }: DataTableProps) {
  return (
    <details className={`simulation-table-section ${compact ? "simulation-table-section-compact" : ""}`} open={defaultOpen}>
      <summary>
        <span>{title}</span>
        <small>{rows.length} rows</small>
      </summary>
      {rows.length === 0 ? (
        <p className="table-empty">{emptyMessage}</p>
      ) : (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key}>{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${row.id ?? row.sim_id ?? index}-${row.sim_time ?? row.event_time ?? index}`}>
                  {columns.map((column) => {
                    const value = row[column.key];
                    return (
                      <td key={column.key} data-numeric={isNumericValue(value) ? "true" : undefined}>
                        {formatTableValue(value)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  );
}

export function SimulationTables({ data, defaultOpen = false, compact = false }: SimulationTablesProps) {
  const [selectedSimulationId, setSelectedSimulationId] = useState(allSimulationIds);
  const [selectedEventType, setSelectedEventType] = useState(allEventTypes);
  const simulationOptions = useMemo(() => buildSimulationOptions(data), [data]);
  const simulationFilteredData = useMemo(
    () => ({
      simulations: filterRowsBySimulationId(data.simulations, selectedSimulationId),
      events: filterRowsBySimulationId(data.events, selectedSimulationId),
      telemetry: filterRowsBySimulationId(data.telemetry, selectedSimulationId),
    }),
    [data, selectedSimulationId],
  );
  const eventTypeOptions = useMemo(() => buildEventTypeOptions(simulationFilteredData), [simulationFilteredData]);
  const filteredData = useMemo(
    () => ({
      simulations: simulationFilteredData.simulations,
      events: filterRowsByEventType(simulationFilteredData.events, selectedEventType),
      telemetry: filterRowsByEventType(simulationFilteredData.telemetry, selectedEventType),
    }),
    [simulationFilteredData, selectedEventType],
  );
  const totalEventRows = simulationFilteredData.events.length;

  useEffect(() => {
    if (selectedEventType !== allEventTypes && !eventTypeOptions.some((option) => option.type === selectedEventType)) {
      setSelectedEventType(allEventTypes);
    }
  }, [eventTypeOptions, selectedEventType]);

  useEffect(() => {
    if (selectedSimulationId !== allSimulationIds && !simulationOptions.some((option) => option.id === selectedSimulationId)) {
      setSelectedSimulationId(allSimulationIds);
    }
  }, [selectedSimulationId, simulationOptions]);

  return (
    <div className="simulation-tables">
      {simulationOptions.length > 0 && (
        <div className={`event-filter-bar ${compact ? "event-filter-bar-compact" : ""}`} aria-label="Filter log rows by simulation">
          <div className="event-filter-copy">
            <span>Simulation Filter</span>
            <small>{selectedSimulationId === allSimulationIds ? "Showing all simulations" : `Showing simulation ${selectedSimulationId}`}</small>
          </div>
          <div className="event-filter-actions">
            <button
              type="button"
              className={selectedSimulationId === allSimulationIds ? "active" : undefined}
              aria-pressed={selectedSimulationId === allSimulationIds}
              onClick={() => setSelectedSimulationId(allSimulationIds)}
            >
              All
              <span>{simulationOptions.length}</span>
            </button>
            {simulationOptions.map(({ id, count }) => (
              <button
                type="button"
                key={id}
                className={selectedSimulationId === id ? "active" : undefined}
                aria-pressed={selectedSimulationId === id}
                onClick={() => setSelectedSimulationId(id)}
              >
                Sim {id}
                <span>{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      {eventTypeOptions.length > 0 && (
        <div className={`event-filter-bar ${compact ? "event-filter-bar-compact" : ""}`} aria-label="Filter log events by type">
          <div className="event-filter-copy">
            <span>Event Filter</span>
            <small>{selectedEventType === allEventTypes ? "Showing all event rows" : `Showing ${selectedEventType}`}</small>
          </div>
          <div className="event-filter-actions">
            <button
              type="button"
              className={selectedEventType === allEventTypes ? "active" : undefined}
              aria-pressed={selectedEventType === allEventTypes}
              onClick={() => setSelectedEventType(allEventTypes)}
            >
              All
              <span>{totalEventRows}</span>
            </button>
            {eventTypeOptions.map(({ type, count }) => (
              <button
                type="button"
                key={type}
                className={selectedEventType === type ? "active" : undefined}
                aria-pressed={selectedEventType === type}
                onClick={() => setSelectedEventType(type)}
              >
                {type}
                <span>{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      <DataTable
        title="Simulations"
        emptyMessage="No simulations saved yet."
        columns={simulationColumns}
        rows={filteredData.simulations}
        defaultOpen={defaultOpen}
        compact={compact}
      />
      <DataTable
        title="Events"
        emptyMessage="No events saved yet."
        columns={eventColumns}
        rows={filteredData.events}
        defaultOpen={defaultOpen}
        compact={compact}
      />
      <DataTable
        title="Event Telemetry"
        emptyMessage="No event telemetry saved yet."
        columns={telemetryColumns}
        rows={filteredData.telemetry}
        defaultOpen={defaultOpen}
        compact={compact}
      />
    </div>
  );
}

export function latestNumericValue(rows: TableRow[], key: string) {
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const value = asNumber(rows[index][key]);
    if (value !== null) {
      return value;
    }
  }

  return null;
}

export default function SimulationTable() {
  const [data, setData] = useState<SimulationTableData>(emptySimulationTableData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadData = async () => {
      try {
        setData(await fetchSimulationTableData());
        setError("");
      } catch (err) {
        console.error("Error loading simulation tables:", err);
        setError("Could not load simulation data.");
      } finally {
        setLoading(false);
      }
    };

    loadData();
    const intervalId = window.setInterval(loadData, 500);
    return () => window.clearInterval(intervalId);
  }, []);

  if (loading) {
    return <p className="panel-message">Loading simulation data...</p>;
  }

  if (error) {
    return <p className="panel-message panel-message-error">{error}</p>;
  }

  return <SimulationTables data={data} />;
}
