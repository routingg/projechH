import { client } from "./client";
import type { UserProfile } from "../types/user";
import type { Itinerary } from "../types/itinerary";

export async function postItinerary(
  user_profile: UserProfile,
  travel_date?: string,
  selected_place_ids?: string[]
): Promise<Itinerary> {
  const { data } = await client.post<Itinerary>("/api/itinerary", {
    user_profile,
    travel_date,
    selected_place_ids: selected_place_ids ?? [],
  });
  return data;
}
