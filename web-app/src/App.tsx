import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
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
  Trash2,
  ZoomIn,
  ZoomOut,
  type LucideIcon,
} from "lucide-react";
import {
  DATABASE_REFRESH_OPTIONS_MS,
  DEFAULT_DATABASE_REFRESH_MS,
  DEFAULT_LIVE_REFRESH_MS,
  emptySimulationTableData,
  fetchRealtimeUnitIds,
  fetchRobotData,
  fetchSimulationOptions,
  fetchSimulationTableData,
  isDatabaseRefreshMs,
  isLiveRefreshMs,
  isUnitId,
  type DatabaseRefreshMs,
  type LiveRefreshMs,
  LIVE_REFRESH_OPTIONS_MS,
  type SimulationDataFilters,
  type SimulationOption,
  type SimulationTableData,
  type TableRow,
} from "./data";
import { createGoal, goalsForUnit, loadGoalsConfig, moveGoal, removeGoal, type GoalPoint, type MoveDirection } from "./goals";
import { LiveMap } from "./LiveMap";
import SimulationTable, {
  SimulationTables,
  latestNumericValue,
} from "./SimulationTable";
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
  unitId: string;
  time: number;
};

type GoalOrderProps = {
  goals: GoalPoint[];
  selectedGoalName: string | null;
  status: string;
  onMoveGoal: (goalIndex: number, direction: MoveDirection) => void;
  onCreateGoal: (name: string, coordinates: [number, number]) => Promise<void>;
  onRemoveGoal: (goalIndex: number) => void;
  onSelectGoal: (goalName: string) => void;
};

type AppState = {
  robotData: RobotData | null;
};

type FleetUnitData = {
  data: RobotData | null;
  error: string;
};

type FleetDataByUnitId = Record<string, FleetUnitData>;

type CommandShellProps = {
  state: AppState;
  emergencyStopActive: boolean | null;
  emergencyStopLoading: boolean;
  emergencyStopError: string;
  onEmergencyStopToggle: () => void;
  databaseRefreshMs: DatabaseRefreshMs;
  onDatabaseRefreshChange: (refreshMs: DatabaseRefreshMs) => void;
  liveRefreshMs: LiveRefreshMs;
  onLiveRefreshChange: (refreshMs: LiveRefreshMs) => void;
  showLiveRefreshControl: boolean;
  showDatabaseRefreshControl: boolean;
  showRobotSelector: boolean;
  selectedUnitId: string | null;
  availableUnitIds: string[];
  unitDiscoveryLoading: boolean;
  unitDiscoveryError: string;
  onSelectedUnitChange: (unitId: string) => void;
  showSimulationSelector: boolean;
  selectedSimulationId: number | null;
  availableSimulationIds: number[];
  onSelectedSimulationChange: (simId: number | null) => void;
  children: ReactNode;
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
const databasePollingRoutes = new Set(["/", "/logs", "/tables"]);
const realtimePollingRoutes = new Set(["/", "/map", "/fleet", "/logs", "/tables"]);
const robotSelectorRoutes = new Set(["/", "/map", "/logs", "/tables"]);
const databaseRefreshStorageKey = "agv-database-refresh-ms";
const liveRefreshStorageKey = "agv-live-refresh-ms";
const selectedUnitStorageKey = "agv-selected-unit-id";
const realtimeUnitDiscoveryRefreshMs = 3_000;

function compareNumericUnitIds(left: string, right: string) {
  if (left.length !== right.length) {
    return left.length - right.length;
  }
  return left.localeCompare(right);
}

function readStoredDatabaseRefreshMs(): DatabaseRefreshMs {
  try {
    const storedValue = Number(window.localStorage.getItem(databaseRefreshStorageKey));
    return isDatabaseRefreshMs(storedValue) ? storedValue : DEFAULT_DATABASE_REFRESH_MS;
  } catch {
    return DEFAULT_DATABASE_REFRESH_MS;
  }
}

function readStoredLiveRefreshMs(): LiveRefreshMs {
  try {
    const storedValue = Number(window.localStorage.getItem(liveRefreshStorageKey));
    return isLiveRefreshMs(storedValue) ? storedValue : DEFAULT_LIVE_REFRESH_MS;
  } catch {
    return DEFAULT_LIVE_REFRESH_MS;
  }
}

function formatLiveRefreshMs(refreshMs: LiveRefreshMs) {
  return refreshMs < 1_000 ? `${refreshMs}ms` : `${refreshMs / 1_000}s`;
}

function readStoredSelectedUnitId(): string | null {
  try {
    const storedUnitId = window.localStorage.getItem(selectedUnitStorageKey);
    return isUnitId(storedUnitId) ? storedUnitId : null;
  } catch {
    return null;
  }
}

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

function LiveImage({ alt, label, src, unitId, time }: LiveImageProps) {
  const query = new URLSearchParams({ unit_id: unitId, t: String(time) });

  return (
    <div className="feed-frame">
      <div className="feed-frame-header">
        <span>{label}</span>
        <StatusPill tone="critical">Live</StatusPill>
      </div>
      <img src={`${src}?${query.toString()}`} alt={alt} />
    </div>
  );
}

function GoalOrder({ goals, selectedGoalName, status, onMoveGoal, onCreateGoal, onRemoveGoal, onSelectGoal }: GoalOrderProps) {
  const statusTone = status === "Loaded" ? "success" : status === "Load failed" ? "critical" : "warning";
  const [newGoalName, setNewGoalName] = useState("");
  const [newGoalX, setNewGoalX] = useState("");
  const [newGoalY, setNewGoalY] = useState("");
  const [createError, setCreateError] = useState("");

  async function handleCreateGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newGoalName.trim();
    const x = Number(newGoalX);
    const y = Number(newGoalY);
    if (name.length === 0 || newGoalX.trim() === "" || newGoalY.trim() === "" || !Number.isFinite(x) || !Number.isFinite(y)) {
      setCreateError("Enter a goal name and two finite coordinates.");
      return;
    }

    setCreateError("");
    try {
      await onCreateGoal(name, [x, y]);
      setNewGoalName("");
      setNewGoalX("");
      setNewGoalY("");
    } catch {
      setCreateError("Could not create the goal.");
    }
  }

  return (
    <article className="metric-card metric-group-card goal-order-card">
      <div className="metric-card-heading">
        <span>Goal Order</span>
        <StatusPill tone={statusTone}>{status}</StatusPill>
      </div>
      {goals.length === 0 ? (
        <p className="panel-message">No route is configured for the selected unit.</p>
      ) : (
        <ol className="goal-order-list">
          {goals.map(({ name, coordinates }, index) => (
            <li key={`${name}-${index}`} className="goal-order-item">
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
                <button type="button" aria-label={`Move ${name} up`} disabled={status !== "Loaded" || index === 0} onClick={() => onMoveGoal(index, -1)}>
                  <ChevronUp size={15} aria-hidden="true" />
                </button>
                <button type="button" aria-label={`Move ${name} down`} disabled={status !== "Loaded" || index === goals.length - 1} onClick={() => onMoveGoal(index, 1)}>
                  <ChevronDown size={15} aria-hidden="true" />
                </button>
                <button type="button" className="goal-remove-button" aria-label={`Remove ${name}`} disabled={status !== "Loaded" || goals.length <= 1} onClick={() => onRemoveGoal(index)}>
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </span>
            </li>
          ))}
        </ol>
      )}
      <form className="goal-create-form" onSubmit={handleCreateGoal}>
        <label>
          <span>Goal name</span>
          <input value={newGoalName} disabled={status !== "Loaded"} onChange={(event) => setNewGoalName(event.target.value)} />
        </label>
        <label>
          <span>X</span>
          <input type="number" step="any" value={newGoalX} disabled={status !== "Loaded"} onChange={(event) => setNewGoalX(event.target.value)} />
        </label>
        <label>
          <span>Y</span>
          <input type="number" step="any" value={newGoalY} disabled={status !== "Loaded"} onChange={(event) => setNewGoalY(event.target.value)} />
        </label>
        <button type="submit" disabled={status !== "Loaded"}>Add Goal</button>
      </form>
      {createError && <p className="goal-create-error">{createError}</p>}
    </article>
  );
}

function CommandShell({
  state,
  emergencyStopActive,
  emergencyStopLoading,
  emergencyStopError,
  onEmergencyStopToggle,
  databaseRefreshMs,
  onDatabaseRefreshChange,
  liveRefreshMs,
  onLiveRefreshChange,
  showLiveRefreshControl,
  showDatabaseRefreshControl,
  showRobotSelector,
  selectedUnitId,
  availableUnitIds,
  unitDiscoveryLoading,
  unitDiscoveryError,
  onSelectedUnitChange,
  showSimulationSelector,
  selectedSimulationId,
  availableSimulationIds,
  onSelectedSimulationChange,
  children,
}: CommandShellProps) {
  const runtime = state.robotData ? formatRuntime(state.robotData.time) : "No signal";
  const selectedUnitMissing = selectedUnitId !== null && !availableUnitIds.includes(selectedUnitId);
  const selectedUnitUnavailable = selectedUnitMissing && !unitDiscoveryLoading && unitDiscoveryError === "";
  const showControlDock = showRobotSelector || showSimulationSelector || showLiveRefreshControl || showDatabaseRefreshControl;

  function handleDatabaseRefreshChange(value: string) {
    const refreshMs = Number(value);
    if (isDatabaseRefreshMs(refreshMs)) {
      onDatabaseRefreshChange(refreshMs);
    }
  }

  function handleLiveRefreshChange(value: string) {
    const refreshMs = Number(value);
    if (isLiveRefreshMs(refreshMs)) {
      onLiveRefreshChange(refreshMs);
    }
  }

  function handleSelectedSimulationChange(value: string) {
    if (value === "") {
      onSelectedSimulationChange(null);
      return;
    }

    const simId = Number(value);
    if (Number.isInteger(simId) && availableSimulationIds.includes(simId)) {
      onSelectedSimulationChange(simId);
    }
  }

  return (
    <div className={`command-center${showControlDock ? " has-page-controls" : ""}`}>
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

        <button
          type="button"
          className="emergency-stop"
          aria-pressed={emergencyStopActive ?? undefined}
          disabled={emergencyStopLoading || emergencyStopActive === null}
          onClick={onEmergencyStopToggle}
        >
          <ShieldAlert size={18} aria-hidden="true" />
          {emergencyStopLoading ? "Checking Stop" : emergencyStopActive === null ? "Emergency Stop Unavailable" : emergencyStopActive ? "Resume Robots" : "Emergency Stop"}
        </button>
        {emergencyStopError && <p className="emergency-stop-error" role="alert">{emergencyStopError}</p>}

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

      {showControlDock && (
        <section className="page-control-dock" aria-label="Page controls">
          {showRobotSelector && (
            <label className="robot-select-control">
              <span>Robot</span>
              <select
                aria-label="Selected robot"
                value={selectedUnitId ?? ""}
                disabled={availableUnitIds.length === 0}
                onChange={(event) => onSelectedUnitChange(event.target.value)}
              >
                {selectedUnitId === null && (
                  <option value="" disabled>
                    {unitDiscoveryLoading ? "Discovering…" : "No active units"}
                  </option>
                )}
                {selectedUnitMissing && (
                  <option value={selectedUnitId} disabled>
                    Unit {selectedUnitId} ({selectedUnitUnavailable ? "unavailable" : "checking…"})
                  </option>
                )}
                {availableUnitIds.map((unitId) => (
                  <option key={unitId} value={unitId}>
                    Unit {unitId}
                  </option>
                ))}
              </select>
            </label>
          )}
          {showSimulationSelector && (
            <label className="simulation-select-control">
              <span>Simulation</span>
              <select
                aria-label="Selected simulation"
                value={selectedSimulationId === null ? "" : String(selectedSimulationId)}
                disabled={selectedUnitId === null}
                onChange={(event) => handleSelectedSimulationChange(event.target.value)}
              >
                <option value="">All simulations</option>
                {availableSimulationIds.map((simId) => (
                  <option key={simId} value={simId}>
                    Sim {simId}
                  </option>
                ))}
              </select>
            </label>
          )}
          {showLiveRefreshControl && (
            <label className="live-refresh-control">
              <span>Live refresh</span>
              <select
                aria-label="Live refresh interval"
                value={liveRefreshMs}
                onChange={(event) => handleLiveRefreshChange(event.target.value)}
              >
                {LIVE_REFRESH_OPTIONS_MS.map((refreshMs) => (
                  <option key={refreshMs} value={refreshMs}>
                    {formatLiveRefreshMs(refreshMs)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {showDatabaseRefreshControl && (
            <label className="database-refresh-control">
              <span>Database refresh</span>
              <select
                aria-label="Database refresh interval"
                value={databaseRefreshMs}
                onChange={(event) => handleDatabaseRefreshChange(event.target.value)}
              >
                {DATABASE_REFRESH_OPTIONS_MS.map((refreshMs) => (
                  <option key={refreshMs} value={refreshMs}>
                    {refreshMs / 1_000}s
                  </option>
                ))}
              </select>
            </label>
          )}
        </section>
      )}

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
  goalsStatus,
  onMoveGoal,
  onCreateGoal,
  onRemoveGoal,
  onSelectGoal,
  selectedSimulationId,
}: {
  data: RobotData | null;
  tableData: SimulationTableData;
  tableError: string;
  tablesLoading: boolean;
  goalOrder: GoalPoint[];
  selectedGoalName: string | null;
  goalsStatus: string;
  onMoveGoal: (goalIndex: number, direction: MoveDirection) => void;
  onCreateGoal: (name: string, coordinates: [number, number]) => Promise<void>;
  onRemoveGoal: (goalIndex: number) => void;
  onSelectGoal: (goalName: string) => void;
  selectedSimulationId: number | null;
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
          status={goalsStatus}
          onMoveGoal={onMoveGoal}
          onCreateGoal={onCreateGoal}
          onRemoveGoal={onRemoveGoal}
          onSelectGoal={onSelectGoal}
        />
      </section>

      <section className="dashboard-grid">
        <Panel title="Warehouse Map" eyebrow="AGV-UNIT-00 active" className="dashboard-map-panel">
          <LiveMap data={data} />
        </Panel>

        <div className="dashboard-feeds">
          <LiveImage alt="Robot AI camera feed" label="AI Camera" src="/api/camera-feed" unitId={data.unit_id} time={data.time} />
          <LiveImage alt="Live local planner grid" label="Local Planner / Lidar" src="/api/local-planner-grid" unitId={data.unit_id} time={data.time} />
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
        {!tablesLoading && !tableError && <SimulationTables data={tableData} compact selectedSimulationId={selectedSimulationId} />}
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
          <LiveImage alt="Live local planner grid" label="Local Planner" src="/api/local-planner-grid" unitId={data.unit_id} time={data.time} />
          <LiveImage alt="Robot AI camera feed" label="AI Camera" src="/api/camera-feed" unitId={data.unit_id} time={data.time} />
        </div>
      </section>
    </div>
  );
}

function FleetPage({
  unitIds,
  fleetData,
  unitDiscoveryLoading,
  unitDiscoveryError,
}: {
  unitIds: string[];
  fleetData: FleetDataByUnitId;
  unitDiscoveryLoading: boolean;
  unitDiscoveryError: string;
}) {
  const liveUnits = unitIds.flatMap((unitId) => {
    const data = fleetData[unitId]?.data;
    return data === null || data === undefined ? [] : [data];
  });
  const liveSimulationIds = new Set(liveUnits.map((data) => data.sim_id));
  const waitingUnitCount = unitIds.length - liveUnits.length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Live Fleet"
        title="Fleet Status"
        description="Live summaries for every unit with a validated realtime snapshot."
      />

      {unitDiscoveryError && <div className="signal-banner">{unitDiscoveryError}</div>}

      <section className="metric-grid metric-grid-top">
        <MetricCard label="Known Units" value={String(unitIds.length)} detail="Validated realtime snapshots" tone="primary" icon={Bot} />
        <MetricCard label="Live Telemetry" value={`${liveUnits.length} / ${unitIds.length}`} detail="Current unit payloads" icon={Radio} />
        <MetricCard label="Active Simulations" value={String(liveSimulationIds.size)} detail="Across reporting units" icon={Activity} />
        <MetricCard label="Units Waiting" value={String(waitingUnitCount)} detail="Loading or unavailable telemetry" icon={AlertTriangle} />
      </section>

      {unitDiscoveryLoading && unitIds.length === 0 ? (
        <Panel title="Discovering Units" eyebrow="Fleet Status">
          <p className="panel-message">Waiting for realtime AGV unit discovery...</p>
        </Panel>
      ) : unitIds.length === 0 ? (
        <Panel title="No Active Units" eyebrow="Fleet Status">
          <p className="panel-message">No valid realtime unit snapshots are currently available.</p>
        </Panel>
      ) : (
        <section className="fleet-grid">
          {unitIds.map((unitId) => {
            const snapshot = fleetData[unitId];
            const data = snapshot?.data ?? null;
            const statusTone = data ? "success" : snapshot?.error ? "critical" : "warning";
            const statusLabel = data ? "Live" : snapshot?.error ? "Unavailable" : "Loading";

            return (
              <article className="unit-card" key={unitId}>
                <div className="unit-card-header">
                  <div className="unit-avatar">
                    <Bot size={30} aria-hidden="true" />
                  </div>
                  <div>
                    <h2>Unit {unitId}</h2>
                    <span>{data ? `Simulation ${data.sim_id}` : "Realtime telemetry"}</span>
                  </div>
                  <StatusPill tone={statusTone}>{statusLabel}</StatusPill>
                </div>
                <div className="unit-card-grid">
                  <MetricCard label="Mission Runtime" value={data ? formatRuntimeShort(data.time) : "N/A"} className="unit-small-card" />
                  <MetricCard label="Current linear velocity" value={data ? fmt(data.current_velocities.linear) : "N/A"} unit="m/s" className="unit-small-card" />
                  <MetricCard label="Current angular velocity" value={data ? fmt(data.current_velocities.angular) : "N/A"} unit="rad/s" className="unit-small-card" />
                  <MetricCard label="Distance Error" value={data ? fmt(data.errors.distance, 4) : "N/A"} unit="m" className="unit-error-card" />
                  <MetricCard label="Heading Error" value={data ? fmt(data.errors.heading, 4) : "N/A"} unit="rad" className="unit-error-card" />
                  <MetricGroupCard
                    label="Goal"
                    className="unit-goal-card"
                    items={[
                      { label: "Goal X", value: data ? fmt(data.goal_position.x) : "N/A", unit: "m" },
                      { label: "Goal Y", value: data ? fmt(data.goal_position.y) : "N/A", unit: "m" },
                    ]}
                  />
                </div>
                <div className="unit-status-line">
                  <Radio size={16} aria-hidden="true" />
                  <span>{data ? "Unit-specific telemetry via `/api/realtime`" : snapshot?.error || "Requesting unit-specific telemetry..."}</span>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}

function LogAnalysisPage({
  tableData,
  loading,
  error,
  selectedSimulationId,
}: {
  tableData: SimulationTableData;
  loading: boolean;
  error: string;
  selectedSimulationId: number | null;
}) {
  const latestTelemetry = latestRow(tableData.telemetry);
  const currentLinear = latestNumericValue(tableData.telemetry, "current_vel_linear");
  const headingError = latestNumericValue(tableData.telemetry, "error_heading");
  const chartTelemetryRows = telemetryRowsForCharts(
    tableData.telemetry,
    tableData.simulations,
    selectedSimulationId,
  );

  return (
    <div className="page">
      <PageHeader eyebrow="Diagnostics" title="Log Analysis" description="Post-run analysis built from MySQL simulation, event, and event telemetry snapshots." />

      <section className="metric-grid metric-grid-top">
        <MetricCard label="Simulations" value={String(tableData.simulations.length)} icon={Database} />
        <MetricCard label="Events" value={String(tableData.events.length)} icon={Activity} />
        <MetricCard label="Telemetry Rows" value={String(tableData.telemetry.length)} icon={Terminal} />
        <MetricCard label="Current linear velocity" value={fmt(currentLinear)} unit="m/s" tone="primary" icon={Gauge} />
      </section>

      <section className="chart-grid">
        <Panel title="Linear Velocity Over Time" eyebrow="current_vel_linear">
          <LineChart rows={chartTelemetryRows} valueKey="current_vel_linear" />
        </Panel>
        <Panel title="Heading Error Deviation" eyebrow="error_heading">
          <LineChart rows={chartTelemetryRows} valueKey="error_heading" tone="muted" />
        </Panel>
      </section>

      <Panel
        title="Event Telemetry"
        eyebrow={latestTelemetry ? `Latest: ${latestTelemetry.event_time ?? "N/A"} | Heading ${fmt(headingError, 4)} rad` : "No telemetry rows"}
      >
        {loading && <p className="panel-message">Loading simulation data...</p>}
        {!loading && error && <p className="panel-message panel-message-error">{error}</p>}
        {!loading && !error && <SimulationTables data={tableData} defaultOpen selectedSimulationId={selectedSimulationId} />}
      </Panel>
    </div>
  );
}

function telemetryRowsForCharts(
  telemetryRows: TableRow[],
  simulationRows: TableRow[],
  selectedSimulationId: number | null,
) {
  const effectiveSimulationId = selectedSimulationId ?? latestSimulationId(simulationRows);
  if (effectiveSimulationId === null) {
    return [];
  }

  return telemetryRows
    .filter((row) => Number(row.sim_id) === effectiveSimulationId)
    .slice(-100);
}

function latestSimulationId(rows: TableRow[]) {
  let latestId: number | null = null;
  for (const row of rows) {
    const simulationId = Number(row.id);
    if (Number.isInteger(simulationId) && simulationId > 0 && (latestId === null || simulationId > latestId)) {
      latestId = simulationId;
    }
  }
  return latestId;
}

function LineChart({ rows, valueKey, tone = "primary" }: { rows: TableRow[]; valueKey: string; tone?: "primary" | "muted" }) {
  const values = rows.map((row) => Number(row[valueKey])).filter((value) => Number.isFinite(value));
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
      icon: Radio,
      title: "Start a live session",
      text: "Start MySQL, then the logging server, then press Play in Webots. Start `npm run dev` last—or leave it running, since it will discover robots automatically.",
    },
    {
      icon: Bot,
      title: "Select the correct unit",
      text: "Dashboard, Map, and Log Analysis show one selected robot; Fleet Status is the only all-robot view.",
    },
    {
      icon: ShieldAlert,
      title: "Emergency Stop",
      text: "Stops all active robots without stopping Webots. Use Resume Robots to allow motion again.",
    },
    {
      icon: AlertTriangle,
      title: "Protect the Webots world",
      text: "Keep the warning against using the global save shortcut, since it can remove `.wbt` comments.",
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

function useRealtimeUnits(enabled: boolean) {
  const [unitIds, setUnitIds] = useState<string[]>([]);
  const [unitDiscoveryLoading, setUnitDiscoveryLoading] = useState(true);
  const [unitDiscoveryError, setUnitDiscoveryError] = useState("");

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let alive = true;
    let timeoutId: number | undefined;

    async function loadRealtimeUnits() {
      try {
        const nextUnitIds = await fetchRealtimeUnitIds();
        if (alive) {
          setUnitIds((currentUnitIds) => (
            currentUnitIds.length === nextUnitIds.length &&
            currentUnitIds.every((unitId, index) => unitId === nextUnitIds[index])
              ? currentUnitIds
              : nextUnitIds
          ));
          setUnitDiscoveryError("");
        }
      } catch (error) {
        console.error("Error discovering realtime units:", error);
        if (alive) {
          setUnitDiscoveryError("Could not discover active units.");
        }
      } finally {
        if (alive) {
          setUnitDiscoveryLoading(false);
          timeoutId = window.setTimeout(loadRealtimeUnits, realtimeUnitDiscoveryRefreshMs);
        }
      }
    }

    loadRealtimeUnits();
    return () => {
      alive = false;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [enabled]);

  return { unitIds, unitDiscoveryLoading, unitDiscoveryError };
}

function useRobotData(
  selectedUnitId: string | null,
  enabled: boolean,
  refreshMs: LiveRefreshMs,
  availableUnitIds: string[],
  unitDiscoveryLoading: boolean,
  unitDiscoveryError: string,
) {
  const [robotData, setRobotData] = useState<RobotData | null>(null);
  const [robotError, setRobotError] = useState("");
  const responseUnitIdRef = useRef<string | null>(null);

  useEffect(() => {
    let alive = true;
    let timeoutId: number | undefined;
    responseUnitIdRef.current = selectedUnitId;
    setRobotData(null);
    setRobotError("");

    if (!enabled) {
      return () => {
        alive = false;
      };
    }

    if (selectedUnitId === null) {
      if (unitDiscoveryLoading) {
        setRobotError("Waiting for active unit discovery...");
      } else if (unitDiscoveryError === "") {
        setRobotError("No active units are currently available.");
      }
      return () => {
        alive = false;
      };
    }

    const realtimeUnitId = selectedUnitId;

    if (
      !unitDiscoveryLoading &&
      unitDiscoveryError === "" &&
      !availableUnitIds.includes(realtimeUnitId)
    ) {
      setRobotError(`Unit ${realtimeUnitId} is unavailable.`);
      return () => {
        alive = false;
      };
    }

    async function loadRobotData() {
      try {
        const data = await fetchRobotData(realtimeUnitId);
        if (alive && responseUnitIdRef.current === realtimeUnitId) {
          setRobotData(data);
          setRobotError("");
        }
      } catch (error) {
        console.error(`Error loading realtime data for unit ${realtimeUnitId}:`, error);
        if (alive && responseUnitIdRef.current === realtimeUnitId) {
          setRobotError(`Could not load realtime data for unit ${realtimeUnitId}.`);
        }
      } finally {
        if (alive && responseUnitIdRef.current === realtimeUnitId) {
          timeoutId = window.setTimeout(loadRobotData, refreshMs);
        }
      }
    }

    loadRobotData();
    return () => {
      alive = false;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [availableUnitIds, enabled, refreshMs, selectedUnitId, unitDiscoveryError, unitDiscoveryLoading]);

  return { robotData, robotError };
}

function useFleetRobotData(enabled: boolean, unitIds: string[], refreshMs: LiveRefreshMs) {
  const [fleetData, setFleetData] = useState<FleetDataByUnitId>({});

  useEffect(() => {
    let alive = true;
    let timeoutId: number | undefined;

    if (!enabled || unitIds.length === 0) {
      setFleetData({});
      return () => {
        alive = false;
      };
    }

    async function loadFleetData() {
      const nextFleetEntries = await Promise.all(
        unitIds.map(async (unitId): Promise<[string, FleetUnitData]> => {
          try {
            return [unitId, { data: await fetchRobotData(unitId), error: "" }];
          } catch {
            return [unitId, { data: null, error: `Could not load realtime data for unit ${unitId}.` }];
          }
        }),
      );

      if (alive) {
        setFleetData(Object.fromEntries(nextFleetEntries));
        timeoutId = window.setTimeout(loadFleetData, refreshMs);
      }
    }

    loadFleetData();
    return () => {
      alive = false;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [enabled, refreshMs, unitIds]);

  return fleetData;
}

function useSimulationOptions(refreshMs: DatabaseRefreshMs, enabled: boolean) {
  const [simulationOptions, setSimulationOptions] = useState<SimulationOption[]>([]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let alive = true;
    let timeoutId: number | undefined;

    async function loadSimulationOptions() {
      try {
        const nextOptions = await fetchSimulationOptions();
        if (alive) {
          setSimulationOptions(nextOptions);
        }
      } catch (error) {
        console.error("Error loading simulation options:", error);
      } finally {
        if (alive) {
          timeoutId = window.setTimeout(loadSimulationOptions, refreshMs);
        }
      }
    }

    loadSimulationOptions();
    return () => {
      alive = false;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [enabled, refreshMs]);

  return simulationOptions;
}

function useSimulationTables(
  refreshMs: DatabaseRefreshMs,
  enabled: boolean,
  selectedUnitId: string | null,
  selectedSimulationId: number | null,
) {
  const [tableData, setTableData] = useState<SimulationTableData>(emptySimulationTableData);
  const [tablesLoading, setTablesLoading] = useState(true);
  const [tableError, setTableError] = useState("");
  const filterKey = `${enabled ? "enabled" : "disabled"}:${selectedUnitId ?? "none"}:${selectedSimulationId ?? "all"}`;
  const activeFilterKeyRef = useRef(filterKey);
  const automaticPollingEnabled = enabled && selectedUnitId !== null;

  useEffect(() => {
    activeFilterKeyRef.current = filterKey;
    setTableData(emptySimulationTableData);
    setTablesLoading(enabled);
    setTableError("");
  }, [enabled, filterKey]);

  useEffect(() => {
    if (!automaticPollingEnabled || selectedUnitId === null) {
      return;
    }

    let alive = true;
    let timeoutId: number | undefined;
    const requestKey = filterKey;
    const filters: SimulationDataFilters = {
      unitId: selectedUnitId,
      ...(selectedSimulationId === null ? {} : { simId: selectedSimulationId }),
    };

    async function loadTables() {
      try {
        const data = await fetchSimulationTableData(filters);
        if (alive && activeFilterKeyRef.current === requestKey) {
          setTableData(data);
          setTableError("");
        }
      } catch (err) {
        console.error("Error loading simulation tables:", err);
        if (alive && activeFilterKeyRef.current === requestKey) {
          setTableError("Could not load simulation data.");
        }
      } finally {
        if (alive && activeFilterKeyRef.current === requestKey) {
          setTablesLoading(false);
          timeoutId = window.setTimeout(loadTables, refreshMs);
        }
      }
    }

    loadTables();
    return () => {
      alive = false;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [automaticPollingEnabled, filterKey, refreshMs, selectedSimulationId, selectedUnitId]);

  return { tableData, tablesLoading, tableError };
}

function useGoalOrder(selectedUnitId: string | null) {
  const [goalConfig, setGoalConfig] = useState<Awaited<ReturnType<typeof loadGoalsConfig>> | null>(null);
  const [selectedGoalName, setSelectedGoalName] = useState<string | null>(null);
  const [goalsStatus, setGoalsStatus] = useState("Loading");
  const goalMutationInFlightRef = useRef(false);
  const goalOrder = useMemo(
    () => (goalConfig === null ? [] : goalsForUnit(goalConfig, selectedUnitId) ?? []),
    [goalConfig, selectedUnitId],
  );

  useEffect(() => {
    async function loadGoalOrder() {
      try {
        const config = await loadGoalsConfig();
        setGoalConfig(config);
        setGoalsStatus("Loaded");
      } catch {
        setGoalConfig(null);
        setGoalsStatus("Load failed");
      }
    }

    loadGoalOrder();
  }, []);

  useEffect(() => {
    setSelectedGoalName((currentSelection) => (
      currentSelection !== null && goalOrder.some((goal) => goal.name === currentSelection)
        ? currentSelection
        : goalOrder[0]?.name ?? null
    ));
  }, [goalOrder]);

  const routeStatus =
    goalsStatus !== "Loaded"
      ? goalsStatus
      : selectedUnitId === null
        ? "Waiting for Unit"
        : goalOrder.length === 0
          ? `No route for Unit ${selectedUnitId}`
          : "Loaded";

  async function handleMoveGoal(goalIndex: number, direction: MoveDirection) {
    if (selectedUnitId === null || goalConfig === null || goalMutationInFlightRef.current) {
      return;
    }

    const goalName = goalOrder[goalIndex]?.name;
    if (goalName === undefined) {
      return;
    }

    goalMutationInFlightRef.current = true;
    setSelectedGoalName(goalName);
    setGoalsStatus("Saving");
    try {
      setGoalConfig(await moveGoal(selectedUnitId, goalIndex, direction));
      setGoalsStatus("Loaded");
    } catch {
      setGoalsStatus("Save failed");
    } finally {
      goalMutationInFlightRef.current = false;
    }
  }

  async function handleCreateGoal(name: string, coordinates: [number, number]) {
    if (selectedUnitId === null || goalConfig === null || goalMutationInFlightRef.current) {
      throw new Error("Goal creation is not available");
    }

    goalMutationInFlightRef.current = true;
    setGoalsStatus("Saving");
    try {
      setGoalConfig(await createGoal(selectedUnitId, name, coordinates));
      setSelectedGoalName(name);
      setGoalsStatus("Loaded");
    } catch (error) {
      setGoalsStatus("Save failed");
      throw error;
    } finally {
      goalMutationInFlightRef.current = false;
    }
  }

  async function handleRemoveGoal(goalIndex: number) {
    if (
      selectedUnitId === null ||
      goalConfig === null ||
      goalMutationInFlightRef.current ||
      goalOrder.length <= 1 ||
      goalOrder[goalIndex] === undefined
    ) {
      return;
    }

    goalMutationInFlightRef.current = true;
    setGoalsStatus("Saving");
    try {
      setGoalConfig(await removeGoal(selectedUnitId, goalIndex));
      setSelectedGoalName(null);
      setGoalsStatus("Loaded");
    } catch {
      setGoalsStatus("Save failed");
    } finally {
      goalMutationInFlightRef.current = false;
    }
  }

  return {
    goalOrder,
    selectedGoalName,
    goalsStatus: routeStatus,
    handleMoveGoal,
    handleCreateGoal,
    handleRemoveGoal,
    setSelectedGoalName,
  };
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

function isEmergencyStopResponse(value: unknown): value is { active: boolean } {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    typeof (value as { active?: unknown }).active === "boolean"
  );
}

async function requestEmergencyStop(method: "GET" | "POST" | "DELETE") {
  const response = await fetch("/api/emergency-stop", { method, cache: "no-store" });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(`Emergency stop request failed (${response.status})`);
  }
  if (!isEmergencyStopResponse(payload)) {
    throw new Error("Emergency stop response is invalid");
  }
  return payload.active;
}

function useEmergencyStop() {
  const [active, setActive] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    requestEmergencyStop("GET")
      .then((nextActive) => {
        if (!cancelled) {
          setActive(nextActive);
          setError("");
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Emergency stop request failed");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function toggleEmergencyStop() {
    if (active === null) {
      return;
    }

    setLoading(true);
    setError("");
    try {
      setActive(await requestEmergencyStop(active ? "DELETE" : "POST"));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Emergency stop request failed");
    } finally {
      setLoading(false);
    }
  }

  return { active, loading, error, toggleEmergencyStop };
}

function RoutedApp() {
  const location = useLocation();
  const [databaseRefreshMs, setDatabaseRefreshMs] = useState<DatabaseRefreshMs>(readStoredDatabaseRefreshMs);
  const [liveRefreshMs, setLiveRefreshMs] = useState<LiveRefreshMs>(readStoredLiveRefreshMs);
  const [selectedUnitId, setSelectedUnitId] = useState<string | null>(readStoredSelectedUnitId);
  const [selectedSimulationId, setSelectedSimulationId] = useState<number | null>(null);
  const { active: emergencyStopActive, loading: emergencyStopLoading, error: emergencyStopError, toggleEmergencyStop } = useEmergencyStop();
  const realtimePollingEnabled = realtimePollingRoutes.has(location.pathname);
  const databasePollingEnabled = databasePollingRoutes.has(location.pathname);
  const showLiveRefreshControl = realtimePollingEnabled;
  const showDatabaseRefreshControl = databasePollingEnabled;
  const showRobotSelector = robotSelectorRoutes.has(location.pathname);
  const showSimulationSelector = databasePollingEnabled;
  const { unitIds, unitDiscoveryLoading, unitDiscoveryError } = useRealtimeUnits(realtimePollingEnabled);
  const simulationOptions = useSimulationOptions(databaseRefreshMs, databasePollingEnabled);
  const availableUnitIds = useMemo(
    () => [...new Set([...unitIds, ...simulationOptions.map((option) => option.unitId)])].sort(compareNumericUnitIds),
    [simulationOptions, unitIds],
  );
  const availableSimulationIds = useMemo(
    () => simulationOptions.find((option) => option.unitId === selectedUnitId)?.simIds ?? [],
    [selectedUnitId, simulationOptions],
  );
  const { robotData, robotError } = useRobotData(
    selectedUnitId,
    realtimePollingEnabled,
    liveRefreshMs,
    unitIds,
    unitDiscoveryLoading,
    unitDiscoveryError,
  );
  const fleetData = useFleetRobotData(location.pathname === "/fleet", unitIds, liveRefreshMs);
  const { tableData, tablesLoading, tableError } = useSimulationTables(
    databaseRefreshMs,
    databasePollingEnabled,
    selectedUnitId,
    selectedSimulationId,
  );
  const {
    goalOrder,
    selectedGoalName,
    goalsStatus,
    handleMoveGoal,
    handleCreateGoal,
    handleRemoveGoal,
    setSelectedGoalName,
  } = useGoalOrder(selectedUnitId);
  const { guide, guideLoading } = useHelpGuide();
  const state: AppState = {
    robotData,
  };

  useEffect(() => {
    if (selectedUnitId === null && availableUnitIds.length > 0) {
      setSelectedUnitId(availableUnitIds[0]);
    }
  }, [availableUnitIds, selectedUnitId]);

  useEffect(() => {
    if (selectedSimulationId !== null && !availableSimulationIds.includes(selectedSimulationId)) {
      setSelectedSimulationId(null);
    }
  }, [availableSimulationIds, selectedSimulationId]);

  useEffect(() => {
    if (selectedUnitId === null) {
      return;
    }

    try {
      window.localStorage.setItem(selectedUnitStorageKey, selectedUnitId);
    } catch {
      // The selected unit remains available for this session when storage is unavailable.
    }
  }, [selectedUnitId]);

  function handleDatabaseRefreshChange(refreshMs: DatabaseRefreshMs) {
    setDatabaseRefreshMs(refreshMs);
    try {
      window.localStorage.setItem(databaseRefreshStorageKey, String(refreshMs));
    } catch {
      // The selected interval still applies for this session when storage is unavailable.
    }
  }

  function handleLiveRefreshChange(refreshMs: LiveRefreshMs) {
    setLiveRefreshMs(refreshMs);
    try {
      window.localStorage.setItem(liveRefreshStorageKey, String(refreshMs));
    } catch {
      // The selected interval still applies for this session when storage is unavailable.
    }
  }

  function handleSelectedUnitChange(unitId: string) {
    if (isUnitId(unitId) && availableUnitIds.includes(unitId)) {
      setSelectedUnitId(unitId);
      setSelectedSimulationId(null);
    }
  }

  function handleSelectedSimulationChange(simId: number | null) {
    if (simId === null || availableSimulationIds.includes(simId)) {
      setSelectedSimulationId(simId);
    }
  }

  return (
    <CommandShell
      state={state}
      emergencyStopActive={emergencyStopActive}
      emergencyStopLoading={emergencyStopLoading}
      emergencyStopError={emergencyStopError}
      onEmergencyStopToggle={toggleEmergencyStop}
      databaseRefreshMs={databaseRefreshMs}
      onDatabaseRefreshChange={handleDatabaseRefreshChange}
      liveRefreshMs={liveRefreshMs}
      onLiveRefreshChange={handleLiveRefreshChange}
      showLiveRefreshControl={showLiveRefreshControl}
      showDatabaseRefreshControl={showDatabaseRefreshControl}
      showRobotSelector={showRobotSelector}
      selectedUnitId={selectedUnitId}
      availableUnitIds={availableUnitIds}
      unitDiscoveryLoading={unitDiscoveryLoading}
      unitDiscoveryError={unitDiscoveryError}
      onSelectedUnitChange={handleSelectedUnitChange}
      showSimulationSelector={showSimulationSelector}
      selectedSimulationId={selectedSimulationId}
      availableSimulationIds={availableSimulationIds}
      onSelectedSimulationChange={handleSelectedSimulationChange}
    >
      {showRobotSelector && unitDiscoveryError && <div className="signal-banner">{unitDiscoveryError}</div>}
      {location.pathname !== "/fleet" && realtimePollingEnabled && robotError && <div className="signal-banner">{robotError}</div>}
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
              goalsStatus={goalsStatus}
              onMoveGoal={handleMoveGoal}
              onCreateGoal={handleCreateGoal}
              onRemoveGoal={handleRemoveGoal}
              onSelectGoal={setSelectedGoalName}
              selectedSimulationId={selectedSimulationId}
            />
          }
        />
        <Route path="/map" element={<MapPage data={robotData} />} />
        <Route
          path="/fleet"
          element={
            <FleetPage
              unitIds={unitIds}
              fleetData={fleetData}
              unitDiscoveryLoading={unitDiscoveryLoading}
              unitDiscoveryError={unitDiscoveryError}
            />
          }
        />
        <Route
          path="/logs"
          element={
            <LogAnalysisPage
              tableData={tableData}
              loading={tablesLoading}
              error={tableError}
              selectedSimulationId={selectedSimulationId}
            />
          }
        />
        <Route path="/help" element={<HelpCenterPage guide={guide} loading={guideLoading} />} />
        <Route path="/support" element={<Navigate to="/help" replace />} />
        <Route
          path="/tables"
          element={
            <SimulationTable
              data={tableData}
              loading={tablesLoading}
              error={tableError}
              selectedSimulationId={selectedSimulationId}
            />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </CommandShell>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <RoutedApp />
    </BrowserRouter>
  );
}
