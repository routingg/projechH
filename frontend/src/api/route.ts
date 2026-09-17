import { client } from "./client";

export interface RoutePoint {
  lat: number;
  lng: number;
}

export interface RouteResponse {
  path: RoutePoint[];
  distance_m: number | null;
  duration_s: number | null;
  source: "kakao" | "straight";
}

export async function postRoute(points: RoutePoint[]): Promise<RouteResponse> {
  const { data } = await client.post<RouteResponse>("/api/route", { points });
  return data;
}
