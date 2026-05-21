import { useEffect, useState } from "react";
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
  return (
    <div className="simulation-tables">
      <DataTable
        title="Simulations"
        emptyMessage="No simulations saved yet."
        columns={simulationColumns}
        rows={data.simulations}
        defaultOpen={defaultOpen}
        compact={compact}
      />
      <DataTable
        title="Events"
        emptyMessage="No events saved yet."
        columns={eventColumns}
        rows={data.events}
        defaultOpen={defaultOpen}
        compact={compact}
      />
      <DataTable
        title="Event Telemetry"
        emptyMessage="No event telemetry saved yet."
        columns={telemetryColumns}
        rows={data.telemetry}
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
