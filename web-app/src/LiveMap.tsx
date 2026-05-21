import { MAP_BOUNDS, OBSTACLES, POINTS, type MapPoint } from "./mapData";
import type { RobotData } from "./types";

type LiveMapProps = {
  data: RobotData;
  variant?: "panel" | "expanded";
  showGrid?: boolean;
  showObstacles?: boolean;
  showPoints?: boolean;
  showPath?: boolean;
  zoom?: number;
};

const y = (value: number) => -value;
const mapWidth = MAP_BOUNDS.maxX - MAP_BOUNDS.minX;
const mapHeight = MAP_BOUNDS.maxY - MAP_BOUNDS.minY;
const ticks = (min: number, max: number, step: number) =>
  Array.from({ length: Math.floor((max - min) / step) + 1 }, (_, index) => min + index * step);

const xTicks = ticks(Math.ceil(MAP_BOUNDS.minX / 5) * 5, Math.floor(MAP_BOUNDS.maxX / 5) * 5, 5);
const yTicks = ticks(Math.ceil(MAP_BOUNDS.minY / 5) * 5, Math.floor(MAP_BOUNDS.maxY / 5) * 5, 5);
const legendItems = ["agv", "dropoff", "pickup", "charging", "goal", "path"] as const;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

function viewBoxFor(robotX: number, robotY: number, zoom: number) {
  const normalizedZoom = clamp(zoom, 1, 3);
  const visibleWidth = mapWidth / normalizedZoom;
  const visibleHeight = mapHeight / normalizedZoom;
  const centerX = clamp(robotX, MAP_BOUNDS.minX + visibleWidth / 2, MAP_BOUNDS.maxX - visibleWidth / 2);
  const centerY = clamp(robotY, MAP_BOUNDS.minY + visibleHeight / 2, MAP_BOUNDS.maxY - visibleHeight / 2);
  const minX = centerX - visibleWidth / 2;
  const maxY = centerY + visibleHeight / 2;

  return `${minX} ${y(maxY)} ${visibleWidth} ${visibleHeight}`;
}

function PointMarker({ point }: { point: MapPoint }) {
  const [name, x, pointY, kind] = point;
  const svgY = y(pointY);
  const label = kind === "charging" ? "" : name.split(" ").at(-1);
  const marker =
    kind === "pickup" ? (
      <circle cx={x} cy={svgY} r="0.45" />
    ) : kind === "charging" ? (
      <polygon points={`${x + 0.15},${svgY - 0.75} ${x - 0.55},${svgY + 0.05} ${x - 0.05},${svgY + 0.05} ${x - 0.2},${svgY + 0.75} ${x + 0.55},${svgY - 0.2} ${x + 0.05},${svgY - 0.2}`} />
    ) : (
      <rect x={x - 0.45} y={svgY - 0.45} width="0.9" height="0.9" rx="0.08" />
    );

  return (
    <g className={`map-point map-point-${kind}`}>
      {marker}
      {label && <text x={x} y={svgY - 0.85}>{label}</text>}
    </g>
  );
}

export function LiveMap({
  data,
  variant = "panel",
  showGrid = true,
  showObstacles = true,
  showPoints = true,
  showPath = true,
  zoom = 1,
}: LiveMapProps) {
  const { goal_position: goal, next_point: nextPoint, state } = data;
  const { x: robotX, y: robotY, theta } = state;
  const headingX = robotX + 1.5 * Math.cos(theta);
  const headingY = robotY + 1.5 * Math.sin(theta);
  const viewBox = zoom > 1 ? viewBoxFor(robotX, robotY, zoom) : `${MAP_BOUNDS.minX} ${y(MAP_BOUNDS.maxY)} ${mapWidth} ${mapHeight}`;

  return (
    <div className={`map-shell map-shell-${variant}`}>
      <svg className="live-map" viewBox={viewBox} role="img" aria-label="AGV live position map">
        <rect className="map-background" x={MAP_BOUNDS.minX} y={y(MAP_BOUNDS.maxY)} width={mapWidth} height={mapHeight} />

        {showGrid && (
          <g className="map-grid">
            {xTicks.map((tick) => (
              <line key={`x-${tick}`} x1={tick} y1={y(MAP_BOUNDS.minY)} x2={tick} y2={y(MAP_BOUNDS.maxY)} />
            ))}
            {yTicks.map((tick) => (
              <line key={`y-${tick}`} x1={MAP_BOUNDS.minX} y1={y(tick)} x2={MAP_BOUNDS.maxX} y2={y(tick)} />
            ))}
          </g>
        )}

        {showObstacles && (
          <g className="map-obstacles">
            {OBSTACLES.map(([x, obstacleY, width, height]) => (
              <rect key={`${x}-${obstacleY}`} x={x - width / 2} y={y(obstacleY + height / 2)} width={width} height={height} />
            ))}
          </g>
        )}

        {showPoints && <g className="map-points">{POINTS.map((point) => <PointMarker key={point[0]} point={point} />)}</g>}

        {showPath && (
          <g className="map-active-path">
            <polyline
              points={
                nextPoint
                  ? `${robotX},${y(robotY)} ${nextPoint.x},${y(nextPoint.y)} ${goal.x},${y(goal.y)}`
                  : `${robotX},${y(robotY)} ${goal.x},${y(goal.y)}`
              }
            />
          </g>
        )}

        <g className="map-goal">
          <line x1={goal.x - 0.6} y1={y(goal.y) - 0.6} x2={goal.x + 0.6} y2={y(goal.y) + 0.6} />
          <line x1={goal.x - 0.6} y1={y(goal.y) + 0.6} x2={goal.x + 0.6} y2={y(goal.y) - 0.6} />
        </g>

        <g className="map-robot">
          <circle cx={robotX} cy={y(robotY)} r="0.75" />
          <line x1={robotX} y1={y(robotY)} x2={headingX} y2={y(headingY)} />
        </g>
      </svg>

      <div className="map-legend" aria-label="Map legend">
        {legendItems.map((item) => (
          <span key={item}>
            <i className={`legend-swatch legend-${item}`} />
            {item[0].toUpperCase() + item.slice(1)}
          </span>
        ))}
      </div>
    </div>
  );
}
