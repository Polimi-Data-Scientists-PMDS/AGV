import { useEffect, useState } from 'react';

type TableValue = string | number | boolean | null | undefined;
type TableRow = Record<string, TableValue>;

type Column = {
  key: string;
  label: string;
};

type DataTableProps = {
  title: string;
  emptyMessage: string;
  columns: Column[];
  rows: TableRow[];
};

type SimulationTableData = {
  simulations: TableRow[];
  events: TableRow[];
  telemetry: TableRow[];
};

const parseJsonLines = (text: string): TableRow[] =>
  text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as TableRow);

const fetchJsonLines = async (url: string): Promise<TableRow[]> => {
  const response = await fetch(url);
  return response.ok ? parseJsonLines(await response.text()) : [];
};

const simulationId = (row: TableRow) => row.id ?? row.sim_id;

const latestSimulationRows = (rows: TableRow[]) => {
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

const formatValue = (value: TableValue) => value ?? '';

const DataTable = ({ title, emptyMessage, columns, rows }: DataTableProps) => {
  return (
    <details className="simulation-table-section">
      <summary>
        <h2>{title}</h2>
      </summary>
      {rows.length === 0 ? (
        <p>{emptyMessage}</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table border={1} cellPadding="10" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: '#f4f4f4' }}>
                {columns.map(column => <th key={column.key}>{column.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                // rows use `id` (simulations) or `sim_id` (events/telemetry); fall back to index
                <tr key={`${title}-${row.id ?? row.sim_id ?? index}-${row.sim_time ?? row.event_time ?? index}`}>
                  {columns.map(column => <td key={column.key}>{formatValue(row[column.key])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  );
};

// Keys match the JSONL fields written by robot_log.py
const simulationColumns: Column[] = [
  { key: 'id',                  label: 'Sim ID'      },
  { key: 'controller_version',  label: 'Controller'  },
  { key: 'total_sim_time',      label: 'Total Time'  },
  { key: 'total_idle_time',     label: 'Idle Time'   },
  { key: 'obstacle_count',      label: 'Obstacles'   },
  { key: 'event_count',         label: 'Events'      },
];

const eventColumns: Column[] = [
  { key: 'sim_id',   label: 'Sim ID'   },
  { key: 'sim_time', label: 'Sim Time' },
  { key: 'e_type',   label: 'Type'     },
  { key: 'details',  label: 'Details'  },
];

const telemetryColumns: Column[] = [
  { key: 'sim_id',              label: 'Sim ID'          },
  { key: 'event_time',          label: 'Event Time'      },
  { key: 'e_type',              label: 'Type'            },
  { key: 'state_x',             label: 'State X'         },
  { key: 'state_y',             label: 'State Y'         },
  { key: 'state_theta',         label: 'State Theta'     },
  { key: 'gps_x',               label: 'GPS X'           },
  { key: 'gps_y',               label: 'GPS Y'           },
  { key: 'error_distance',      label: 'Error Distance'  },
  { key: 'error_heading',       label: 'Error Heading'   },
  { key: 'current_vel_linear',  label: 'Current Linear'  },
  { key: 'current_vel_angular', label: 'Current Angular' },
  { key: 'target_vel_linear',   label: 'Target Linear'   },
  { key: 'target_vel_angular',  label: 'Target Angular'  },
  { key: 'next_point_x',        label: 'Next Point X'    },
  { key: 'next_point_y',        label: 'Next Point Y'    },
];

const SimulationTable = () => {
  const [data, setData] = useState<SimulationTableData>({
    simulations: [],
    events: [],
    telemetry: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        // Each endpoint serves the corresponding JSONL file directly.
        // simulations.jsonl is overwritten in-place by robot_log.py so one
        // fetch is enough; no history/current split needed.
        const [simulationRows, events, telemetry] = await Promise.all([
          fetchJsonLines('/api/simulations'),
          fetchJsonLines('/api/events'),
          fetchJsonLines('/api/event-telemetry'),
        ]);

        setData({ simulations: latestSimulationRows(simulationRows), events, telemetry });
        setError('');
      } catch (err) {
        console.error('Error loading simulation tables:', err);
        setError('Could not load simulation data.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
    const intervalId = window.setInterval(loadData, 500);
    return () => window.clearInterval(intervalId);
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      {loading && <p>Loading simulation data...</p>}
      {!loading && error && <p style={{ color: 'red' }}>{error}</p>}
      {!loading && !error && (
        <>
          <DataTable
            title="Simulations"
            emptyMessage="No simulations saved yet."
            columns={simulationColumns}
            rows={data.simulations}
          />
          <DataTable
            title="Events"
            emptyMessage="No events saved yet."
            columns={eventColumns}
            rows={data.events}
          />
          <DataTable
            title="Event Telemetry"
            emptyMessage="No event telemetry saved yet."
            columns={telemetryColumns}
            rows={data.telemetry}
          />
        </>
      )}
    </div>
  );
};

export default SimulationTable;
