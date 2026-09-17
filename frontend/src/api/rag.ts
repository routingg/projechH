import { client } from "./client";
import type { RagAskRequest, RagAskResponse, RagRequest, RagResponse } from "../types/rag";
import type { Recommendation } from "../types/place";

const FACT_LABELS: Record<string, string> = {
  has_accessible_parking: "장애인 주차장",
  has_accessible_toilet: "장애인 화장실",
  has_wheelchair_rental: "휠체어 대여",
  is_indoor: "실내 관광지",
};

/** 추천 결과를 RAG 근거 데이터(candidate_places)로 변환한다. */
export function toCandidatePlaces(recs: Recommendation[]) {
  return recs.map((r) => {
    const verified: string[] = [];
    const unknown: string[] = [];
    (Object.keys(FACT_LABELS) as (keyof typeof r.facts)[]).forEach((key) => {
      const v = r.facts[key];
      if (v === true) verified.push(`${FACT_LABELS[key]} 확인`);
      else if (v === null) unknown.push(`${FACT_LABELS[key]} 미확인`);
    });
    return {
      name: r.name,
      category: r.category,
      accessibility_score: r.accessibility_score,
      weather_risk_score: r.weather_risk_score,
      mobility_feasibility_score: r.mobility_feasibility_score,
      verified_facts: verified,
      unknown_facts: unknown,
    };
  });
}

export async function postRag(payload: RagRequest): Promise<RagResponse> {
  const { data } = await client.post<RagResponse>("/api/rag/recommend", payload);
  return data;
}

export async function postRagAsk(payload: RagAskRequest): Promise<RagAskResponse> {
  const { data } = await client.post<RagAskResponse>("/api/rag/ask", payload);
  return data;
}
