export type RecommendationLevel =
  | "recommended"
  | "conditional"
  | "not_recommended";

export interface PlaceFacts {
  has_accessible_parking: boolean | null;
  has_accessible_toilet: boolean | null;
  has_wheelchair_rental: boolean | null;
  is_indoor: boolean | null;
}

export interface Recommendation {
  place_id: string;
  name: string;
  category: string;
  address?: string | null;
  lat?: number | null;
  lon?: number | null;
  image_urls?: string[];
  accessibility_score: number;
  weather_risk_score: number;
  transport_score: number;
  airport_burden_score: number;
  mobility_feasibility_score: number;
  recommendation_level: RecommendationLevel;
  warnings: string[];
  facts: PlaceFacts;
  /** 자연어 질의 관련도 0~100 (질의 없거나 미매칭이면 null) */
  relevance_score?: number | null;
  /** 질의와 관련된 무장애 문서 스니펫 */
  match_reason?: string[];
  /** 제주데이터허브 무장애여행정보 원문 스니펫 */
  barrier_free_info?: string[];
}
