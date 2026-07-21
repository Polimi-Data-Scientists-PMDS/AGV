export type GoalPoint = {
  name: string;
  coordinates: [number, number];
};

export type GoalsConfig = {
  Goals: GoalPoint[];
  RobotRoutes: Record<string, string[]>;
};

export type MoveDirection = -1 | 1;

function isFiniteCoordinate(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isGoalsConfig(value: unknown): value is GoalsConfig {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const config = value as { Goals?: unknown; RobotRoutes?: unknown };
  if (!Array.isArray(config.Goals) || config.Goals.length === 0 || typeof config.RobotRoutes !== "object" || config.RobotRoutes === null || Array.isArray(config.RobotRoutes)) {
    return false;
  }

  const goalNames = new Set<string>();
  if (!config.Goals.every((goal) => {
    if (typeof goal !== "object" || goal === null || Array.isArray(goal)) {
      return false;
    }
    const point = goal as { name?: unknown; coordinates?: unknown };
    if (
      typeof point.name !== "string" ||
      point.name.length === 0 ||
      goalNames.has(point.name) ||
      !Array.isArray(point.coordinates) ||
      point.coordinates.length !== 2 ||
      !point.coordinates.every(isFiniteCoordinate)
    ) {
      return false;
    }
    goalNames.add(point.name);
    return true;
  })) {
    return false;
  }

  return Object.entries(config.RobotRoutes).every(([unitId, route]) => (
    /^\d+$/.test(unitId) &&
    Array.isArray(route) &&
    route.length > 0 &&
    route.every((goalName) => typeof goalName === "string" && goalNames.has(goalName))
  ));
}

export function goalsForUnit(config: GoalsConfig, unitId: string | null): GoalPoint[] | null {
  if (unitId === null) {
    return null;
  }

  const route = config.RobotRoutes[unitId];
  if (route === undefined) {
    return null;
  }

  const goalByName = new Map(config.Goals.map((goal) => [goal.name, goal]));
  return route.map((goalName) => goalByName.get(goalName) as GoalPoint);
}

export async function loadGoalsConfig(): Promise<GoalsConfig> {
  const response = await fetch("/api/goals", { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Could not load goals config");
  }

  const config: unknown = await response.json();
  if (!isGoalsConfig(config)) {
    throw new Error("Controller goals config is malformed");
  }

  return config;
}

export async function moveGoal(
  unitId: string,
  goalIndex: number,
  direction: MoveDirection,
): Promise<GoalsConfig> {
  if (!/^(0|[1-9]\d*)$/.test(unitId)) {
    throw new Error("Selected unit ID is invalid");
  }
  if (!Number.isInteger(goalIndex) || goalIndex < 0 || (direction !== -1 && direction !== 1)) {
    throw new Error("Goal move request is invalid");
  }

  const response = await fetch("/api/goals", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ unit_id: unitId, goal_index: goalIndex, direction }),
  });

  if (!response.ok) {
    throw new Error("Could not move the selected goal");
  }

  const config: unknown = await response.json();
  if (!isGoalsConfig(config)) {
    throw new Error("Updated controller goals config is malformed");
  }

  return config;
}

export async function createGoal(
  unitId: string,
  name: string,
  coordinates: [number, number],
): Promise<GoalsConfig> {
  if (!/^(0|[1-9]\d*)$/.test(unitId)) {
    throw new Error("Selected unit ID is invalid");
  }
  if (
    name.trim().length === 0 ||
    !coordinates.every((coordinate) => typeof coordinate === "number" && Number.isFinite(coordinate))
  ) {
    throw new Error("Goal create request is invalid");
  }

  const response = await fetch("/api/goals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ unit_id: unitId, name: name.trim(), coordinates }),
  });

  if (!response.ok) {
    throw new Error("Could not create the selected goal");
  }

  const config: unknown = await response.json();
  if (!isGoalsConfig(config)) {
    throw new Error("Updated controller goals config is malformed");
  }

  return config;
}

export async function removeGoal(unitId: string, goalIndex: number): Promise<GoalsConfig> {
  if (!/^(0|[1-9]\d*)$/.test(unitId)) {
    throw new Error("Selected unit ID is invalid");
  }
  if (!Number.isInteger(goalIndex) || goalIndex < 0) {
    throw new Error("Goal remove request is invalid");
  }

  const response = await fetch("/api/goals", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ unit_id: unitId, goal_index: goalIndex }),
  });

  if (!response.ok) {
    throw new Error("Could not remove the selected goal");
  }

  const config: unknown = await response.json();
  if (!isGoalsConfig(config)) {
    throw new Error("Updated controller goals config is malformed");
  }

  return config;
}
