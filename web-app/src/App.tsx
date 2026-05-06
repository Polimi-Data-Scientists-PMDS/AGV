import { useEffect, useState } from "react";
import "./App.css";

type AppProps = { title?: string };

type RobotData = {
  time: number;
  state: {
    x: number;
    y: number;
    theta: number;
  };
  gps: {
    x: number;
    y: number;
  };
  errors: {
    distance: number;
    heading: number;
  };
  current_velocities: {
    linear: number;
    angular: number;
  };
  target_velocities: {
    linear: number;
    angular: number;
  };
  goal_position: {
    x: number;
    y: number;
  };
  next_point: {
    x: number;
    y: number;
  } | null;
};

type MetricProps = {
  label: string;
  value: string;
  unit?: string;
};

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
  children: React.ReactNode;
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


export default function App({ title = "AGV Dashboard" }: AppProps) {
    const [robotData, setRobotData] = useState<RobotData | null>(null);

    useEffect(() => {
        async function loadRobotData() {
            const response = await fetch("/api/realtime-panel")
            const data: RobotData = await response.json();
            setRobotData(data);
        }

        loadRobotData();
        const intervalId = window.setInterval(loadRobotData, 300);

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
            <DashboardSection title="Runtime">
                <MetricRow
                    metrics={[
                        { label: "Current Time", value: robotData.time.toFixed(2), unit: "s" },
                    ]}
                />
            </DashboardSection>

            <DashboardSection title="Targets">
                <MetricRow
                    metrics={[
                        { label: "Goal X", value: robotData.goal_position.x.toFixed(2), unit: "m" },
                        { label: "Goal Y", value: robotData.goal_position.y.toFixed(2), unit: "m" },
                    ]}
                />
                <MetricRow
                    metrics={[
                        { label: "Next Point X", value: robotData.next_point
                            ? robotData.next_point.x.toFixed(2)
                            : "N/A",
                            unit: robotData.next_point ? "m" : undefined,
                        },

                        { label: "Next Point Y", value: robotData.next_point
                            ? robotData.next_point.y.toFixed(2)
                            : "N/A",
                            unit: robotData.next_point ? "m" : undefined,
                        },
                    ]}
                />
            </DashboardSection>

            <DashboardSection title="Coordinates">
                <MetricRow
                    metrics={[
                        { label: "State X", value: robotData.state.x.toFixed(2), unit: "m" },
                        { label: "State Y", value: robotData.state.y.toFixed(2), unit: "m" },
                        { label: "State Theta", value: robotData.state.theta.toFixed(2), unit: "rad" },
                    ]}
                />
                <MetricRow
                    metrics={[
                        { label: "GPS X", value: robotData.gps.x.toFixed(2), unit: "m" },
                        { label: "GPS Y", value: robotData.gps.y.toFixed(2), unit: "m" },
                    ]}
                />
            </DashboardSection>

            <DashboardSection title="Tracking Errors">
                <MetricRow
                    metrics={[
                        { label: "Distance Error", value: robotData.errors.distance.toFixed(4), unit: "m" },
                        { label: "Heading Error", value: robotData.errors.heading.toFixed(4), unit: "rad" },
                    ]}
                />
            </DashboardSection>

            <DashboardSection title="Velocities">
                <MetricRow
                    metrics={[
                        { label: "Current Linear", value: robotData.current_velocities.linear.toFixed(2), unit: "m/s" },
                        { label: "Current Angular", value: robotData.current_velocities.angular.toFixed(2), unit: "rad/s" },
                    ]}
                />
                <MetricRow
                    metrics={[
                        { label: "Target Linear", value: robotData.target_velocities.linear.toFixed(2), unit: "m/s" },
                        { label: "Target Angular", value: robotData.target_velocities.angular.toFixed(2), unit: "rad/s" },
                    ]}
                />
            </DashboardSection>
        </main>
    );
}
