import { useEffect, useState, type ReactNode } from "react";
import { LiveMap } from "./LiveMap";
import type { RobotData } from "./types";
import "./App.css";

type AppProps = { title?: string };

type MetricProps = {
  label: string;
  value: string;
  unit?: string;
};

type MetricSection = {
  title: string;
  rows: MetricProps[][];
};

const fmt = (value: number, digits = 2) => value.toFixed(digits);
const pointMetric = (label: string, value?: number): MetricProps => ({
  label,
  value: value === undefined ? "N/A" : fmt(value),
  unit: value === undefined ? undefined : "m",
});

function Metric({ label, value, unit }: MetricProps) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </span>
    </div>
  );
}

type MetricRowProps = {
  metrics: MetricProps[];
};

function MetricRow({ metrics }: MetricRowProps) {
  return (
    <div className="metric-row">
      {metrics.map((metric) => (
        <Metric key={metric.label} label={metric.label} value={metric.value} unit={metric.unit} />
      ))}
    </div>
  );
}

type DashboardSectionProps = {
  title: string;
  children: ReactNode;
};

function DashboardSection({ title, children }: DashboardSectionProps) {
  return (
    <details className="dashboard-section" open>
      <summary>
        <h2>{title}</h2>
      </summary>
      {children}
    </details>
  );
}

type LiveImageProps = {
  alt: string;
  src: string;
  time: number;
};

function LiveImage({ alt, src, time }: LiveImageProps) {
  return <img className="live-feed-image" src={`${src}?t=${time}`} alt={alt} />;
}

function buildMetricSections(data: RobotData): MetricSection[] {
  const { current_velocities: current, errors, goal_position: goal, gps, next_point: next, state, target_velocities: target } = data;

  return [
    { title: "Runtime", rows: [[{ label: "Current Time", value: fmt(data.time), unit: "s" }]] },
    {
      title: "Targets",
      rows: [
        [pointMetric("Goal X", goal.x), pointMetric("Goal Y", goal.y)],
        [pointMetric("Next Point X", next?.x), pointMetric("Next Point Y", next?.y)],
      ],
    },
    {
      title: "Coordinates",
      rows: [
        [
          pointMetric("State X", state.x),
          pointMetric("State Y", state.y),
          { label: "State Theta", value: fmt(state.theta), unit: "rad" },
        ],
        [pointMetric("GPS X", gps.x), pointMetric("GPS Y", gps.y)],
      ],
    },
    {
      title: "Tracking Errors",
      rows: [[{ label: "Distance Error", value: fmt(errors.distance, 4), unit: "m" }, { label: "Heading Error", value: fmt(errors.heading, 4), unit: "rad" }]],
    },
    {
      title: "Velocities",
      rows: [
        [{ label: "Current Linear", value: fmt(current.linear), unit: "m/s" }, { label: "Current Angular", value: fmt(current.angular), unit: "rad/s" }],
        [{ label: "Target Linear", value: fmt(target.linear), unit: "m/s" }, { label: "Target Angular", value: fmt(target.angular), unit: "rad/s" }],
      ],
    },
  ];
}

export default function App({ title = "AGV Dashboard" }: AppProps) {
  const [robotData, setRobotData] = useState<RobotData | null>(null);

  useEffect(() => {
    async function loadRobotData() {
      const response = await fetch("/api/realtime-panel");
      setRobotData(await response.json());
    }

    loadRobotData();
    const intervalId = window.setInterval(loadRobotData, 50);

    return () => window.clearInterval(intervalId);
  }, []);

  if (robotData === null) {
    return (
      <main className="dashboard">
        <h1>{title}</h1>
        <p className="loading-message">Loading robot data...</p>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <h1>{title}</h1>
      <div className="dashboard-layout">
        <div className="dashboard-data">
          {buildMetricSections(robotData).map(({ title, rows }) => (
            <DashboardSection key={title} title={title}>
              {rows.map((metrics, index) => <MetricRow key={index} metrics={metrics} />)}
            </DashboardSection>
          ))}
        </div>

        <div className="dashboard-visuals">
          <DashboardSection title="Live Map">
            <LiveMap data={robotData} />
          </DashboardSection>

          <div className="live-feed-sections">
            <DashboardSection title="Live Local Planner Grid">
              <LiveImage alt="Live local planner grid" src="/api/local-planner-grid" time={robotData.time} />
            </DashboardSection>

            <DashboardSection title="Robot AI Camera">
              <LiveImage alt="Robot AI camera feed" src="/api/camera-feed" time={robotData.time} />
            </DashboardSection>
          </div>
        </div>
      </div>
    </main>
  );
}
