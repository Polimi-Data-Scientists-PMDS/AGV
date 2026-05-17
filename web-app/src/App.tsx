import { useEffect, useState, type KeyboardEvent, type ReactNode } from "react";
import { initialGoalPoints, loadGoalsConfig, moveGoal, saveGoalsConfig, type GoalPoint, type MoveDirection } from "./goals";
import { LiveMap } from "./LiveMap";
import SimulationTable from "./SimulationTable";
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

type GoalOrderProps = {
  goals: GoalPoint[];
  selectedGoalName: string | null;
  saveStatus: string;
  onMoveGoal: (goalName: string, direction: MoveDirection) => void;
  onSelectGoal: (goalName: string) => void;
};

function GoalOrder({ goals, selectedGoalName, saveStatus, onMoveGoal, onSelectGoal }: GoalOrderProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLOListElement>) {
    if (selectedGoalName === null || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) {
      return;
    }

    event.preventDefault();
    onMoveGoal(selectedGoalName, event.key === "ArrowUp" ? -1 : 1);
  }

  return (
    <ol className="goal-order-list" tabIndex={0} onKeyDown={handleKeyDown}>
      {goals.map(({ name, coordinates }, index) => (
        <li key={name} className="goal-order-item">
          <button
            type="button"
            className="goal-order-select"
            aria-pressed={selectedGoalName === name}
            onClick={() => onSelectGoal(name)}
          >
            <span className="goal-order-index">{index + 1}</span>
            <span className="goal-order-name">{name}</span>
            <span className="goal-order-coordinates">
              x {fmt(coordinates[0])}, y {fmt(coordinates[1])}
            </span>
          </button>

          <span className="goal-order-actions">
            <button
              type="button"
              className="goal-order-action"
              aria-label={`Move ${name} up`}
              disabled={index === 0}
              onClick={() => onMoveGoal(name, -1)}
            >
              ^
            </button>
            <button
              type="button"
              className="goal-order-action"
              aria-label={`Move ${name} down`}
              disabled={index === goals.length - 1}
              onClick={() => onMoveGoal(name, 1)}
            >
              v
            </button>
          </span>
        </li>
      ))}
      <li className="goal-order-status">{saveStatus}</li>
    </ol>
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
  const [goalOrder, setGoalOrder] = useState<GoalPoint[]>(initialGoalPoints);
  const [selectedGoalName, setSelectedGoalName] = useState<string | null>(initialGoalPoints[0]?.name ?? null);
  const [goalsSaveStatus, setGoalsSaveStatus] = useState("Saved");

  useEffect(() => {
    async function loadRobotData() {
      const response = await fetch("/api/realtime-panel");
      setRobotData(await response.json());
    }

    loadRobotData();
    const intervalId = window.setInterval(loadRobotData, 50);

    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    async function loadGoalOrder() {
      try {
        const config = await loadGoalsConfig();
        setGoalOrder(config.Goals);
        setSelectedGoalName((currentSelection) => currentSelection ?? config.Goals[0]?.name ?? null);
      } catch {
        setGoalsSaveStatus("Using local goal order");
      }
    }

    loadGoalOrder();
  }, []);

  function handleMoveGoal(goalName: string, direction: MoveDirection) {
    setSelectedGoalName(goalName);
    setGoalOrder((currentGoalOrder) => {
      const nextGoalOrder = moveGoal(currentGoalOrder, goalName, direction);

      if (nextGoalOrder !== currentGoalOrder) {
        setGoalsSaveStatus("Saving...");
        saveGoalsConfig(nextGoalOrder)
          .then(() => setGoalsSaveStatus("Saved"))
          .catch(() => setGoalsSaveStatus("Save failed"));
      }

      return nextGoalOrder;
    });
  }

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

      {/* Live metrics, map, and camera feeds */}
      <div className="dashboard-layout">
        <div className="dashboard-data">
          {buildMetricSections(robotData).map(({ title, rows }) => (
            <DashboardSection key={title} title={title}>
              {rows.map((metrics, index) => <MetricRow key={index} metrics={metrics} />)}
            </DashboardSection>
          ))}

          <DashboardSection title="Goal Order">
            <GoalOrder
              goals={goalOrder}
              selectedGoalName={selectedGoalName}
              saveStatus={goalsSaveStatus}
              onMoveGoal={handleMoveGoal}
              onSelectGoal={setSelectedGoalName}
            />
          </DashboardSection>
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

      {/* Simulation history tables*/}
      <DashboardSection title="Simulation Log">
        <SimulationTable />
      </DashboardSection>
    </main>
  );
}
