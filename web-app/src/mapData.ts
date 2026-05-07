export type PointKind = "dropoff" | "pickup" | "charging";
export type MapPoint = [name: string, x: number, y: number, kind: PointKind];
export type Obstacle = [x: number, y: number, width: number, height: number];

export const MAP_BOUNDS = { minX: -34.5, maxX: 34.5, minY: -11, maxY: 11 };

export const POINTS: MapPoint[] = [
  ["Dropoff 01", -29.3, 4, "dropoff"],
  ["Pickup 1", -24, 3.5, "pickup"],
  ["Pickup 2", -18.5, 6.25, "pickup"],
  ["Pickup 3", -13.5, 6.25, "pickup"],
  ["Pickup 4", -8.25, 4.5, "pickup"],
  ["Pickup 5", -2, 5.75, "pickup"],
  ["Pickup 6", 3.75, 5.75, "pickup"],
  ["Pickup 7", 18.75, 2.25, "pickup"],
  ["Charging Station", 6.75, -4.5, "charging"],
];

export const OBSTACLES: Obstacle[] = [
  [-24.94, 1.92, 1.2, 3],
  [-19.22, 4, 1, 5],
  [-14.18, 4, 1, 5],
  [-9.34, 3.43, 1, 2],
  [-9.34, 0.92, 3, 4],
  [-2.71, 4, 1, 4],
  [2.96, 4, 1, 4],
  [26.36, -0.1, 12, 3],
  [12.5, -1.08, 6, 2.5],
  [0, 10.9, 69, 0.2],
  [-13.65, -10.9, 41.75, 0.2],
  [20.6, -2.8, 27.6, 0.2],
  [-34.4, 0, 0.2, 21.94],
  [34.4, 4.1, 0.2, 13.8],
  [7.3, -2.45, 0.2, 17.1],
  [-5.09814, -7.46193, 0.5, 7],
  [-28.57, 0, 0.5, 14.71],
];
