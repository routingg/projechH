import { client } from "./client";
import type { UserProfile } from "../types/user";
import type { Recommendation } from "../types/place";

export interface RecommendationRequest {
  user_profile: UserProfile;
  travel_date?: string;
  /** 자연어 질의 — 있으면 무장애 문서 관련도가 랭킹에 결합된다 */
  query?: string;
}

export interface RecommendationResponse {
  recommendations: Recommendation[];
  query_applied: boolean;
}

export async function postRecommendationsFull(
  payload: RecommendationRequest
): Promise<RecommendationResponse> {
  const { data } = await client.post<RecommendationResponse>(
    "/api/recommendations",
    payload
  );
  return data;
}

export async function postRecommendations(
  payload: RecommendationRequest
): Promise<Recommendation[]> {
  return (await postRecommendationsFull(payload)).recommendations;
}
