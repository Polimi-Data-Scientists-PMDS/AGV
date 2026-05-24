import { useEffect, useMemo, useState, type KeyboardEvent, type ReactNode } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Battery,
  Bell,
  Bot,
  ChevronDown,
  ChevronUp,
  CircleQuestionMark,
  Database,
  Gauge,
  Grid3x3,
  Home,
  Map as MapIcon,
  Navigation,
  Radio,
  Route as RouteIcon,
  ShieldAlert,
  Target,
  Terminal,
  Wrench,
  Zap,
  ZoomIn,
  ZoomOut,
  type LucideIcon,
} from "lucide-react";
import { emptySimulationTableData, fetchSimulationTableData, type SimulationTableData, type TableRow } from "./data";
import { initialGoalPoints, loadGoalsConfig, moveGoal, saveGoalsConfig, type GoalPoint, type MoveDirection } from "./goals";
import { LiveMap } from "./LiveMap";
import SimulationTable, { SimulationTables, latestNumericValue } from "./SimulationTable";
import type { RobotData } from "./types";
import "./App.css";

type MetricCardProps = {
  label: string;
  value: string;
  unit?: string;
  detail?: string;
  tone?: "default" | "primary" | "warning" | "critical" | "success";
  icon?: LucideIcon;
  className?: string;
};

type MetricGroupCardProps = {
  label: string;
  items: Array<{ label: string; value: string; unit?: string }>;
  tone?: "default" | "primary" | "warning" | "critical" | "success";
  icon?: LucideIcon;
  className?: string;
};

type PanelProps = {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
};

type LiveImageProps = {
  alt: string;
  label: string;
  src: string;
  time: number;
};

type GoalOrderProps = {
  goals: GoalPoint[];
  selectedGoalName: string | null;
  saveStatus: string;
  onMoveGoal: (goalName: string, direction: MoveDirection) => void;
  onSelectGoal: (goalName: string) => void;
};

type AppState = {
  robotData: RobotData | null;
};

type MarkdownBlock =
  | { type: "heading"; level: 1 | 2 | 3 | 4; text: string }
  | { type: "paragraph"; text: string }
  | { type: "unordered-list"; items: string[] }
  | { type: "ordered-list"; items: string[] };

type MarkdownListBlock = Extract<MarkdownBlock, { type: "unordered-list" | "ordered-list" }>;

const navItems: Array<{ label: string; to: string; icon: LucideIcon }> = [
  { label: "Dashboard", to: "/", icon: Home },
  { label: "Map View", to: "/map", icon: MapIcon },
  { label: "Fleet Status", to: "/fleet", icon: Bot },
  { label: "Log Analysis", to: "/logs", icon: Database },
];

const helpNavItem: { label: string; to: string; icon: LucideIcon } = { label: "Help Center", to: "/help", icon: CircleQuestionMark };
const mobileNavItems = [...navItems, helpNavItem];

const fmt = (value: number | null | undefined, digits = 2) => (value === null || value === undefined || !Number.isFinite(value) ? "N/A" : value.toFixed(digits));

function formatRuntime(seconds: number) {
  if (!Number.isFinite(seconds)) {
    return "N/A";
  }

  const wholeSeconds = Math.floor(seconds);
  const centiseconds = Math.floor((seconds - wholeSeconds) * 100);
  const hours = Math.floor(wholeSeconds / 3600);
  const minutes = Math.floor((wholeSeconds % 3600) / 60);
  const remainingSeconds = wholeSeconds % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}.${centiseconds.toString().padStart(2, "0")}`;
}

function formatRuntimeShort(seconds: number) {
  if (!Number.isFinite(seconds)) {
    return "N/A";
  }

  const wholeSeconds = Math.floor(seconds);
  const minutes = Math.floor(wholeSeconds / 60);
  const remainingSeconds = wholeSeconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function latestRow(rows: TableRow[]) {
  return rows.length > 0 ? rows[rows.length - 1] : null;
}

function parseMarkdown(source: string) {
  const blocks: MarkdownBlock[] = [];
  const paragraphLines: string[] = [];
  const parserState: { activeList: MarkdownListBlock | null } = { activeList: null };

  function flushParagraph() {
    if (paragraphLines.length > 0) {
      blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
      paragraphLines.length = 0;
    }
  }

  function flushList() {
    if (parserState.activeList) {
      blocks.push(parserState.activeList);
      parserState.activeList = null;
    }
  }

  function addListItem(type: MarkdownListBlock["type"], text: string) {
    flushParagraph();

    let activeList = parserState.activeList;
    if (!activeList || activeList.type !== type) {
      flushList();
      activeList = type === "unordered-list" ? { type: "unordered-list", items: [] } : { type: "ordered-list", items: [] };
      parserState.activeList = activeList;
    }

    activeList.items.push(text);
  }

  for (const rawLine of source.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (trimmed === "") {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", level: heading[1].length as 1 | 2 | 3 | 4, text: heading[2] });
      continue;
    }

    const unorderedItem = /^-\s+(.+)$/.exec(trimmed);
    if (unorderedItem) {
      addListItem("unordered-list", unorderedItem[1]);
      continue;
    }

    const orderedItem = /^\d+\.\s+(.+)$/.exec(trimmed);
    if (orderedItem) {
      addListItem("ordered-list", orderedItem[1]);
      continue;
    }

    const activeList = parserState.activeList;
    if (activeList && /^\s+/.test(line) && activeList.items.length > 0) {
      activeList.items[activeList.items.length - 1] = `${activeList.items[activeList.items.length - 1]} ${trimmed}`;
      continue;
    }

    flushList();
    paragraphLines.push(trimmed);
  }

  flushParagraph();
  flushList();
  return blocks;
}

function renderInlineMarkdown(text: string) {
  const parts: ReactNode[] = [];
  const tokenPattern = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let lastIndex = 0;

  for (const match of text.matchAll(tokenPattern)) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith("`")) {
      parts.push(<code key={parts.length}>{token.slice(1, -1)}</code>);
    } else {
      parts.push(<strong key={parts.length}>{token.slice(2, -2)}</strong>);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function renderMarkdownBlock(block: MarkdownBlock, index: number) {
  if (block.type === "heading") {
    if (block.level === 1) {
      return <h1 key={index}>{renderInlineMarkdown(block.text)}</h1>;
    }
    if (block.level === 2) {
      return <h2 key={index}>{renderInlineMarkdown(block.text)}</h2>;
    }
    if (block.level === 3) {
      return <h3 key={index}>{renderInlineMarkdown(block.text)}</h3>;
    }
    return <h4 key={index}>{renderInlineMarkdown(block.text)}</h4>;
  }

  if (block.type === "unordered-list") {
    return (
      <ul key={index}>
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
  }

  if (block.type === "ordered-list") {
    return (
      <ol key={index}>
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>{renderInlineMarkdown(item)}</li>
        ))}
      </ol>
    );
  }

  return <p key={index}>{renderInlineMarkdown(block.text)}</p>;
}

function MarkdownPreview({ source }: { source: string }) {
  const blocks = useMemo(() => parseMarkdown(source), [source]);
  const sections = useMemo(() => {
    const groupedSections: Array<{ title: string | null; level: number | null; blocks: MarkdownBlock[] }> = [];

    blocks.forEach((block) => {
      if (block.type === "heading" && block.level <= 3) {
        groupedSections.push({ title: block.text, level: block.level, blocks: [block] });
        return;
      }

      if (groupedSections.length === 0) {
        groupedSections.push({ title: null, level: null, blocks: [] });
      }

      groupedSections[groupedSections.length - 1].blocks.push(block);
    });

    return groupedSections;
  }, [blocks]);

  return (
    <div className="markdown-preview">
      {sections.map((section, sectionIndex) => {
        const sectionClass =
          section.level === 1 || section.title === null
            ? "markdown-section-intro"
            : section.level === 2
              ? "markdown-section-category"
              : "markdown-section-detail";

        return (
          <section className={`markdown-section-card ${sectionClass}`} key={`${section.title ?? "guide-intro"}-${sectionIndex}`}>
            {section.blocks.map((block, blockIndex) => renderMarkdownBlock(block, sectionIndex * 1000 + blockIndex))}
          </section>
        );
      })}
    </div>
  );
}

function Panel({ title, eyebrow, action, className = "", children }: PanelProps) {
  return (
    <section className={`panel ${className}`}>
      {(title || eyebrow || action) && (
        <div className="panel-heading">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}
            {title && <h2>{title}</h2>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

function MetricCard({ label, value, unit, detail, tone = "default", icon: Icon, className = "" }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card-${tone} ${className}`}>
      <div className="metric-card-heading">
        <span>{label}</span>
        {Icon && <Icon size={18} aria-hidden="true" />}
      </div>
      <strong>
        {value}
        {unit && <em>{unit}</em>}
      </strong>
      {detail && <small>{detail}</small>}
    </article>
  );
}

function MetricGroupCard({ label, items, tone = "default", icon: Icon, className = "" }: MetricGroupCardProps) {
  return (
    <article className={`metric-card metric-group-card metric-card-${tone} ${className}`}>
      <div className="metric-card-heading">
        <span>{label}</span>
        {Icon && <Icon size={18} aria-hidden="true" />}
      </div>
      <div className="metric-subgrid">
        {items.map((item) => (
          <div className="metric-subcard" key={`${label}-${item.label}`}>
            <span>{item.label}</span>
            <strong>
              {item.value}
              {item.unit && <em>{item.unit}</em>}
            </strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function StatusPill({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "primary" | "warning" | "critical" | "success" }) {
  return <span className={`status-pill status-pill-${tone}`}>{children}</span>;
}

function LiveImage({ alt, label, src, time }: LiveImageProps) {
  return (
    <div className="feed-frame">
      <div className="feed-frame-header">
        <span>{label}</span>
        <StatusPill tone="critical">Live</StatusPill>
      </div>
      <img src={`${src}?t=${time}`} alt={alt} />
    </div>
  );
}

function GoalOrder({ goals, selectedGoalName, saveStatus, onMoveGoal, onSelectGoal }: GoalOrderProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLOListElement>) {
    if (selectedGoalName === null || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) {
      return;
    }

    event.preventDefault();
    onMoveGoal(selectedGoalName, event.key === "ArrowUp" ? -1 : 1);
  }

  return (
    <article className="metric-card metric-group-card goal-order-card">
      <div className="metric-card-heading">
        <span>Goal Order</span>
        <StatusPill tone={saveStatus === "Saved" ? "success" : saveStatus === "Save failed" ? "critical" : "warning"}>{saveStatus}</StatusPill>
      </div>
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
              <button type="button" aria-label={`Move ${name} up`} disabled={index === 0} onClick={() => onMoveGoal(name, -1)}>
                <ChevronUp size={15} aria-hidden="true" />
              </button>
              <button type="button" aria-label={`Move ${name} down`} disabled={index === goals.length - 1} onClick={() => onMoveGoal(name, 1)}>
                <ChevronDown size={15} aria-hidden="true" />
              </button>
            </span>
          </li>
        ))}
      </ol>
    </article>
  );
}

function CommandShell({ state, children }: { state: AppState; children: ReactNode }) {
  const runtime = state.robotData ? formatRuntime(state.robotData.time) : "No signal";

  return (
    <div className="command-center">
      <header className="topbar">
        <div className="brand-lockup">
          <Bot size={28} aria-hidden="true" />
          <span>AGV Command Center</span>
        </div>
        <nav className="top-nav" aria-label="Primary">
          {navItems.map(({ label, to }) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : undefined)} end={to === "/"}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="topbar-actions">
          <button type="button" aria-label="Notifications">
            <Bell size={20} aria-hidden="true" />
          </button>
          <NavLink to={helpNavItem.to} aria-label={helpNavItem.label} className={({ isActive }) => (isActive ? "active" : undefined)}>
            <CircleQuestionMark size={20} aria-hidden="true" />
          </NavLink>
        </div>
      </header>

      <aside className="sidebar">
        <div className="operator-card">
          <span className="operator-avatar">OP</span>
          <div>
            <strong>Operator-01</strong>
            <span>Warehouse Delta</span>
          </div>
        </div>

        <button type="button" className="emergency-stop">
          <ShieldAlert size={18} aria-hidden="true" />
          Emergency Stop
        </button>

        <nav className="side-nav" aria-label="Command modules">
          {navItems.map(({ label, to, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : undefined)} end={to === "/"}>
              <Icon size={20} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-status-row">
            <StatusPill tone={state.robotData ? "success" : "critical"}>{state.robotData ? "Live Signal" : "No Signal"}</StatusPill>
            <span>{runtime}</span>
          </div>
          <NavLink to={helpNavItem.to} className={({ isActive }) => `sidebar-help-link${isActive ? " active" : ""}`}>
            <CircleQuestionMark size={20} aria-hidden="true" />
            <span>{helpNavItem.label}</span>
          </NavLink>
        </div>
      </aside>

      <main className="content-shell">{children}</main>

      <nav className="mobile-nav" aria-label="Mobile command modules">
        {mobileNavItems.map(({ label, to, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : undefined)} end={to === "/"}>
            <Icon size={20} aria-hidden="true" />
            <span>{label.split(" ")[0]}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function DashboardPage({
  data,
  tableData,
  tableError,
  tablesLoading,
  goalOrder,
  selectedGoalName,
  goalsSaveStatus,
  onMoveGoal,
  onSelectGoal,
}: {
  data: RobotData | null;
  tableData: SimulationTableData;
  tableError: string;
  tablesLoading: boolean;
  goalOrder: GoalPoint[];
  selectedGoalName: string | null;
  goalsSaveStatus: string;
  onMoveGoal: (goalName: string, direction: MoveDirection) => void;
  onSelectGoal: (goalName: string) => void;
}) {
  if (!data) {
    return <LoadingPanel title="Dashboard" message="Waiting for realtime AGV telemetry..." />;
  }

  const telemetryGroups = [
    {
      title: "State",
      className: "telemetry-category-state telemetry-category-large",
      metrics: [
        { label: "State X", value: fmt(data.state.x), unit: "m" },
        { label: "State Y", value: fmt(data.state.y), unit: "m" },
        { label: "State Theta", value: fmt(data.state.theta), unit: "rad" },
      ],
    },
    {
      title: "Velocities",
      className: "telemetry-category-velocities telemetry-category-large",
      metrics: [
        { label: "Current Linear", value: fmt(data.current_velocities.linear), unit: "m/s" },
        { label: "Current Angular", value: fmt(data.current_velocities.angular), unit: "rad/s" },
        { label: "Target Linear", value: fmt(data.target_velocities.linear), unit: "m/s" },
        { label: "Target Angular", value: fmt(data.target_velocities.angular), unit: "rad/s" },
      ],
    },
    {
      title: "Coordinates",
      className: "telemetry-category-coordinates telemetry-category-compact",
      metrics: [
        { label: "GPS X", value: fmt(data.gps.x), unit: "m" },
        { label: "GPS Y", value: fmt(data.gps.y), unit: "m" },
      ],
    },
    {
      title: "Errors",
      className: "telemetry-category-errors telemetry-category-compact",
      metrics: [
        { label: "Distance Error", value: fmt(data.errors.distance, 4), unit: "m" },
        { label: "Heading Error", value: fmt(data.errors.heading, 4), unit: "rad" },
      ],
    },
  ];

  return (
    <div className="page page-dashboard">
      <PageHeader
        eyebrow="Main Command"
        title="Dashboard"
        description="Realtime mission monitor for the active AGV unit, preserving the current telemetry, map, feed, and log data."
      />

      <section className="metric-grid metric-grid-top">
        <MetricCard label="Mission Runtime" value={formatRuntime(data.time)} detail={`${fmt(data.time)} raw seconds`} tone="primary" icon={Activity} />
        <MetricCard label="Active Unit" value="1 / 1" detail="UNIT-00 online" icon={Bot} />
        <MetricGroupCard
          label="Nav. Coordinates"
          icon={Navigation}
          className="metric-group-nav"
          items={[
            { label: "State X", value: fmt(data.state.x), unit: "m" },
            { label: "State Y", value: fmt(data.state.y), unit: "m" },
            { label: "Theta", value: fmt(data.state.theta), unit: "rad" },
          ]}
        />
        <MetricGroupCard
          label="Goal Target"
          icon={Target}
          tone="primary"
          className="metric-group-goal"
          items={[
            { label: "Goal X", value: fmt(data.goal_position.x), unit: "m" },
            { label: "Goal Y", value: fmt(data.goal_position.y), unit: "m" },
            { label: "Next X", value: fmt(data.next_point?.x), unit: data.next_point ? "m" : undefined },
            { label: "Next Y", value: fmt(data.next_point?.y), unit: data.next_point ? "m" : undefined },
          ]}
        />
        <GoalOrder
          goals={goalOrder}
          selectedGoalName={selectedGoalName}
          saveStatus={goalsSaveStatus}
          onMoveGoal={onMoveGoal}
          onSelectGoal={onSelectGoal}
        />
      </section>

      <section className="dashboard-grid">
        <Panel title="Warehouse Map" eyebrow="AGV-UNIT-00 active" className="dashboard-map-panel">
          <LiveMap data={data} />
        </Panel>

        <div className="dashboard-feeds">
          <LiveImage alt="Robot AI camera feed" label="AI Camera" src="/api/camera-feed" time={data.time} />
          <LiveImage alt="Live local planner grid" label="Local Planner / Lidar" src="/api/local-planner-grid" time={data.time} />
        </div>
      </section>

      <Panel title="Realtime Telemetry" eyebrow="Current payload">
        <div className="telemetry-category-grid">
          {telemetryGroups.map((group) => (
            <section className={`telemetry-category ${group.className}`} key={group.title}>
              <h3>{group.title}</h3>
              <div className="telemetry-category-metrics">
                {group.metrics.map((item) => (
                  <MetricCard key={item.label} {...item} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </Panel>

      <Panel title="Simulation Logs" eyebrow="Collapsed by default">
        {tablesLoading && <p className="panel-message">Loading simulation data...</p>}
        {!tablesLoading && tableError && <p className="panel-message panel-message-error">{tableError}</p>}
        {!tablesLoading && !tableError && <SimulationTables data={tableData} compact />}
      </Panel>
    </div>
  );
}

function MapPage({ data }: { data: RobotData | null }) {
  const [zoom, setZoom] = useState(1);
  const [layers, setLayers] = useState({ grid: true, obstacles: true, points: true, path: true });

  if (!data) {
    return <LoadingPanel title="Map View" message="Waiting for realtime map coordinates..." />;
  }

  const toggleLayer = (key: keyof typeof layers) => setLayers((current) => ({ ...current, [key]: !current[key] }));

  return (
    <div className="page page-map">
      <PageHeader eyebrow="Spatial Analysis" title="Map View" description="Expanded SVG warehouse view for the current single AGV unit." />

      <section className="map-workspace">
        <div className="map-toolbar panel">
          <div className="toolbar-group">
            <button type="button" className={layers.grid ? "active" : ""} onClick={() => toggleLayer("grid")}>
              <Grid3x3 size={16} aria-hidden="true" />
              Grid
            </button>
            <button type="button" className={layers.obstacles ? "active" : ""} onClick={() => toggleLayer("obstacles")}>
              <AlertTriangle size={16} aria-hidden="true" />
              Obstacles
            </button>
            <button type="button" className={layers.path ? "active" : ""} onClick={() => toggleLayer("path")}>
              <RouteIcon size={16} aria-hidden="true" />
              Path
            </button>
            <button type="button" className={layers.points ? "active" : ""} onClick={() => toggleLayer("points")}>
              <Target size={16} aria-hidden="true" />
              Goals
            </button>
          </div>
          <div className="toolbar-group">
            <button type="button" onClick={() => setZoom((value) => Math.max(1, value - 0.25))} aria-label="Zoom out">
              <ZoomOut size={16} aria-hidden="true" />
            </button>
            <span>{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={() => setZoom((value) => Math.min(3, value + 0.25))} aria-label="Zoom in">
              <ZoomIn size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        <Panel className="map-expanded-panel">
          <LiveMap
            data={data}
            variant="expanded"
            zoom={zoom}
            showGrid={layers.grid}
            showObstacles={layers.obstacles}
            showPoints={layers.points}
            showPath={layers.path}
          />
        </Panel>

        <Panel title="Active Unit Dashboard" eyebrow="UNIT-00" className="map-pointer-card">
          <p>Current map analysis is following UNIT-00 from the live telemetry stream.</p>
          <NavLink to="/" className="dashboard-pointer-link">
            Open Dashboard
          </NavLink>
        </Panel>

        <div className="map-feed-strip">
          <LiveImage alt="Live local planner grid" label="Local Planner" src="/api/local-planner-grid" time={data.time} />
          <LiveImage alt="Robot AI camera feed" label="AI Camera" src="/api/camera-feed" time={data.time} />
        </div>
      </section>
    </div>
  );
}

function FleetPage({ data }: { data: RobotData | null }) {
  if (!data) {
    return <LoadingPanel title="Fleet Status" message="Waiting for active unit telemetry..." />;
  }

  return (
    <div className="page">
      <PageHeader eyebrow="Fleet Ready / Single Unit" title="Fleet Status" description="The layout is ready for multiple units, but the current data source exposes only UNIT-00." />

      <section className="metric-grid metric-grid-top">
        <MetricCard label="Total Active" value="1 / 1" detail="Current realtime unit" tone="primary" icon={Bot} />
        <MetricCard label="Idle Units" value="0" detail="Not present in current data" icon={Battery} />
        <MetricCard label="Maintenance Required" value="N/A" detail="No maintenance feed available" icon={Wrench} />
        <MetricCard label="Average Battery" value="N/A" detail="No battery field available" icon={Battery} />
      </section>

      <section className="fleet-grid">
        <article className="unit-card">
          <div className="unit-card-header">
            <div className="unit-avatar">
              <Bot size={30} aria-hidden="true" />
            </div>
            <div>
              <h2>UNIT-00</h2>
              <span>ID: AGV-SINGLE-UNIT</span>
            </div>
            <StatusPill tone="success">Active</StatusPill>
          </div>
          <div className="unit-card-grid">
            <MetricCard label="Mission Runtime" value={formatRuntimeShort(data.time)} className="unit-small-card" />
            <MetricCard label="Current linear velocity" value={fmt(data.current_velocities.linear)} unit="m/s" className="unit-small-card" />
            <MetricCard label="Current angular velocity" value={fmt(data.current_velocities.angular)} unit="rad/s" className="unit-small-card" />
            <MetricCard label="Distance Error" value={fmt(data.errors.distance, 4)} unit="m" className="unit-error-card" />
            <MetricCard label="Heading Error" value={fmt(data.errors.heading, 4)} unit="rad" className="unit-error-card" />
            <MetricGroupCard
              label="Goal"
              className="unit-goal-card"
              items={[
                { label: "Goal X", value: fmt(data.goal_position.x), unit: "m" },
                { label: "Goal Y", value: fmt(data.goal_position.y), unit: "m" },
              ]}
            />
          </div>
          <div className="unit-status-line">
            <Radio size={16} aria-hidden="true" />
            <span>Connected through `/api/realtime-panel`</span>
          </div>
        </article>
      </section>
    </div>
  );
}

function LogAnalysisPage({ tableData, loading, error }: { tableData: SimulationTableData; loading: boolean; error: string }) {
  const latestTelemetry = latestRow(tableData.telemetry);
  const currentLinear = latestNumericValue(tableData.telemetry, "current_vel_linear");
  const headingError = latestNumericValue(tableData.telemetry, "error_heading");

  return (
    <div className="page">
      <PageHeader eyebrow="Diagnostics" title="Log Analysis" description="Post-run analysis built only from simulations, events, and event telemetry JSONL data." />

      <section className="metric-grid metric-grid-top">
        <MetricCard label="Simulations" value={String(tableData.simulations.length)} icon={Database} />
        <MetricCard label="Events" value={String(tableData.events.length)} icon={Activity} />
        <MetricCard label="Telemetry Rows" value={String(tableData.telemetry.length)} icon={Terminal} />
        <MetricCard label="Current linear velocity" value={fmt(currentLinear)} unit="m/s" tone="primary" icon={Gauge} />
      </section>

      <section className="chart-grid">
        <Panel title="Linear Velocity Over Time" eyebrow="current_vel_linear">
          <LineChart rows={tableData.telemetry} valueKey="current_vel_linear" />
        </Panel>
        <Panel title="Heading Error Deviation" eyebrow="error_heading">
          <LineChart rows={tableData.telemetry} valueKey="error_heading" tone="muted" />
        </Panel>
      </section>

      <Panel
        title="Event Telemetry"
        eyebrow={latestTelemetry ? `Latest: ${latestTelemetry.event_time ?? "N/A"} | Heading ${fmt(headingError, 4)} rad` : "No telemetry rows"}
      >
        {loading && <p className="panel-message">Loading simulation data...</p>}
        {!loading && error && <p className="panel-message panel-message-error">{error}</p>}
        {!loading && !error && <SimulationTables data={tableData} defaultOpen />}
      </Panel>
    </div>
  );
}

function LineChart({ rows, valueKey, tone = "primary" }: { rows: TableRow[]; valueKey: string; tone?: "primary" | "muted" }) {
  const values = rows.map((row) => Number(row[valueKey])).filter((value) => Number.isFinite(value)).slice(-48);
  const path = useMemo(() => buildChartPath(values), [values]);

  if (values.length === 0) {
    return <p className="panel-message">No numeric telemetry values available.</p>;
  }

  return (
    <svg className={`line-chart line-chart-${tone}`} viewBox="0 0 100 42" role="img" aria-label={`${valueKey} chart`}>
      <path className="chart-baseline" d="M0 32 H100" />
      <path className="chart-path" d={path} />
    </svg>
  );
}

function buildChartPath(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values
    .map((value, index) => {
      const x = values.length === 1 ? 0 : (index / (values.length - 1)) * 100;
      const yValue = 36 - ((value - min) / range) * 28;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${yValue.toFixed(2)}`;
    })
    .join(" ");
}

function HelpCenterPage({ guide, loading }: { guide: string; loading: boolean }) {
  const cards = [
    {
      icon: Zap,
      title: "Initialize The AGV",
      text: "Run `./setup.sh`, use the printed Python interpreter in Webots, then launch the React dashboard with `cd web-app` and `npm run dev`.",
    },
    {
      icon: AlertTriangle,
      title: "Resolve Project Warnings",
      text: "Never save the world directly from Webots with the global save shortcut because it overwrites `.wbt` comments.",
    },
    {
      icon: RouteIcon,
      title: "Inspect Path Visibility",
      text: "Use the realtime dashboard to monitor telemetry, the local planning grid, and the AI camera feed while the AGV is running.",
    },
    {
      icon: Database,
      title: "Prepare Log Storage",
      text: "Start the `agv-logger` MySQL container, create `agv_data`, and initialize tables from `Database_Structure.sql`.",
    },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Operator Support Portal"
        title="Help Center"
        description="All support content on this page is sourced from README.md and docs/web-app-user-guide.md"
      />

      <section className="help-grid">
        {cards.map(({ icon: Icon, title, text }) => (
          <article className="help-card" key={title}>
            <Icon size={24} aria-hidden="true" />
            <h2>{title}</h2>
            <p>{text}</p>
          </article>
        ))}
      </section>

      <Panel eyebrow="docs/web-app-user-guide.md">
        {loading ? <p className="panel-message">Loading web-app-user-guide.md...</p> : <MarkdownPreview source={guide} />}
      </Panel>
    </div>
  );
}

function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="page-header">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function LoadingPanel({ title, message }: { title: string; message: string }) {
  return (
    <div className="page">
      <PageHeader eyebrow="Awaiting Data" title={title} description={message} />
      <Panel>
        <p className="panel-message">No realtime payload is currently available.</p>
      </Panel>
    </div>
  );
}

function useRobotData() {
  const [robotData, setRobotData] = useState<RobotData | null>(null);
  const [robotError, setRobotError] = useState("");

  useEffect(() => {
    let alive = true;

    async function loadRobotData() {
      try {
        const response = await fetch("/api/realtime-panel", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("No realtime panel data found");
        }
        const data = (await response.json()) as RobotData;
        if (alive) {
          setRobotData(data);
          setRobotError("");
        }
      } catch {
        if (alive) {
          setRobotError("No realtime panel data found.");
        }
      }
    }

    loadRobotData();
    const intervalId = window.setInterval(loadRobotData, 50);
    return () => {
      alive = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return { robotData, robotError };
}

function useSimulationTables() {
  const [tableData, setTableData] = useState<SimulationTableData>(emptySimulationTableData);
  const [tablesLoading, setTablesLoading] = useState(true);
  const [tableError, setTableError] = useState("");

  useEffect(() => {
    let alive = true;

    async function loadTables() {
      try {
        const data = await fetchSimulationTableData();
        if (alive) {
          setTableData(data);
          setTableError("");
        }
      } catch (err) {
        console.error("Error loading simulation tables:", err);
        if (alive) {
          setTableError("Could not load simulation data.");
        }
      } finally {
        if (alive) {
          setTablesLoading(false);
        }
      }
    }

    loadTables();
    const intervalId = window.setInterval(loadTables, 500);
    return () => {
      alive = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return { tableData, tablesLoading, tableError };
}

function useGoalOrder() {
  const [goalOrder, setGoalOrder] = useState<GoalPoint[]>(initialGoalPoints);
  const [selectedGoalName, setSelectedGoalName] = useState<string | null>(initialGoalPoints[0]?.name ?? null);
  const [goalsSaveStatus, setGoalsSaveStatus] = useState("Saved");

  useEffect(() => {
    async function loadGoalOrder() {
      try {
        const config = await loadGoalsConfig();
        setGoalOrder(config.Goals);
        setSelectedGoalName((currentSelection) => currentSelection ?? config.Goals[0]?.name ?? null);
        setGoalsSaveStatus("Saved");
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

  return { goalOrder, selectedGoalName, goalsSaveStatus, handleMoveGoal, setSelectedGoalName };
}

function useHelpGuide() {
  const [guide, setGuide] = useState("");
  const [guideLoading, setGuideLoading] = useState(true);

  useEffect(() => {
    async function loadGuide() {
      try {
        const response = await fetch("/api/help-guide", { cache: "no-store" });
        setGuide(response.ok ? await response.text() : "docs/web-app-user-guide.md could not be loaded.");
      } finally {
        setGuideLoading(false);
      }
    }

    loadGuide();
  }, []);

  return { guide, guideLoading };
}

export default function App() {
  const { robotData, robotError } = useRobotData();
  const { tableData, tablesLoading, tableError } = useSimulationTables();
  const { goalOrder, selectedGoalName, goalsSaveStatus, handleMoveGoal, setSelectedGoalName } = useGoalOrder();
  const { guide, guideLoading } = useHelpGuide();
  const state: AppState = {
    robotData,
  };

  return (
    <BrowserRouter>
      <CommandShell state={state}>
        {robotError && <div className="signal-banner">{robotError}</div>}
        <Routes>
          <Route
            path="/"
            element={
              <DashboardPage
                data={robotData}
                tableData={tableData}
                tablesLoading={tablesLoading}
                tableError={tableError}
                goalOrder={goalOrder}
                selectedGoalName={selectedGoalName}
                goalsSaveStatus={goalsSaveStatus}
                onMoveGoal={handleMoveGoal}
                onSelectGoal={setSelectedGoalName}
              />
            }
          />
          <Route path="/map" element={<MapPage data={robotData} />} />
          <Route path="/fleet" element={<FleetPage data={robotData} />} />
          <Route path="/logs" element={<LogAnalysisPage tableData={tableData} loading={tablesLoading} error={tableError} />} />
          <Route path="/help" element={<HelpCenterPage guide={guide} loading={guideLoading} />} />
          <Route path="/support" element={<Navigate to="/help" replace />} />
          <Route path="/tables" element={<SimulationTable />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </CommandShell>
    </BrowserRouter>
  );
}
