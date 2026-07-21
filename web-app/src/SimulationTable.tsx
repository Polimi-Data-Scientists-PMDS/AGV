import { useEffect, useMemo, useState } from "react";
import {
  asNumber,
  eventColumns,
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
  selectedSimulationId: number | null;
  defaultOpen?: boolean;
  compact?: boolean;
};

type SimulationTablePageProps = {
  data: SimulationTableData;
  loading: boolean;
  error: string;
  selectedSimulationId: number | null;
};

const allEventTypes = "__ALL_EVENT_TYPES__";

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

export function SimulationTables({
  data,
  defaultOpen = false,
  compact = false,
  selectedSimulationId,
}: SimulationTablesProps) {
  const [selectedEventType, setSelectedEventType] = useState(allEventTypes);
  const eventTypeOptions = useMemo(() => buildEventTypeOptions(data), [data]);
  const filteredData = useMemo(
    () => ({
      simulations: data.simulations,
      events: filterRowsByEventType(data.events, selectedEventType),
      telemetry: filterRowsByEventType(data.telemetry, selectedEventType),
    }),
    [data, selectedEventType],
  );
  const totalEventRows = data.events.length;
  const hasNoMatchingUnitSimulation =
    selectedSimulationId !== null &&
    data.simulations.length === 0 &&
    data.events.length === 0 &&
    data.telemetry.length === 0;

  useEffect(() => {
    if (selectedEventType !== allEventTypes && !eventTypeOptions.some((option) => option.type === selectedEventType)) {
      setSelectedEventType(allEventTypes);
    }
  }, [eventTypeOptions, selectedEventType]);

  return (
    <div className="simulation-tables">
      {hasNoMatchingUnitSimulation && (
        <p className="simulation-selection-empty">
          No records match this unit and simulation combination. The unit and simulation may exist individually but may not belong together.
        </p>
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

export default function SimulationTable({
  data,
  loading,
  error,
  selectedSimulationId,
}: SimulationTablePageProps) {
  if (loading) {
    return <p className="panel-message">Loading simulation data...</p>;
  }

  if (error) {
    return <p className="panel-message panel-message-error">{error}</p>;
  }

  return (
    <SimulationTables
      data={data}
      selectedSimulationId={selectedSimulationId}
    />
  );
}
