import { client } from "./client";
import type { AirportPlan } from "../types/airport";

export interface AirportPlanRequest {
  departure_time: string;
  wheelchair_type?: string;
  has_companion?: boolean;
}

export async function postAirportPlan(
  payload: AirportPlanRequest
): Promise<AirportPlan> {
  const { data } = await client.post<AirportPlan>(
    "/api/airport/departure-plan",
    payload
  );
  return data;
}
