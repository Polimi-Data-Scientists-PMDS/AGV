import goalsConfig from "./goals.config.json";

export type GoalPoint = {
  name: string;
  coordinates: [number, number];
};

export type GoalsConfig = {
  Goals: GoalPoint[];
};

export type MoveDirection = -1 | 1;

export const initialGoalPoints: GoalPoint[] = (goalsConfig as GoalsConfig).Goals;

export function moveGoal(goals: GoalPoint[], goalName: string, direction: MoveDirection): GoalPoint[] {
  const index = goals.findIndex((goal) => goal.name === goalName);
  const nextIndex = index + direction;

  if (index === -1 || nextIndex < 0 || nextIndex >= goals.length) {
    return goals;
  }

  const reorderedGoals = [...goals];
  [reorderedGoals[index], reorderedGoals[nextIndex]] = [reorderedGoals[nextIndex], reorderedGoals[index]];
  return reorderedGoals;
}

export function buildGoalsConfig(goals: GoalPoint[]): GoalsConfig {
  return { Goals: goals };
}

export async function loadGoalsConfig(): Promise<GoalsConfig> {
  const response = await fetch("/api/goals", { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Could not load goals config");
  }

  return response.json();
}

export async function saveGoalsConfig(goals: GoalPoint[]): Promise<GoalsConfig> {
  const response = await fetch("/api/goals", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildGoalsConfig(goals)),
  });

  if (!response.ok) {
    throw new Error("Could not save goals config");
  }

  return response.json();
}
