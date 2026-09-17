export interface RagCandidatePlace {
  name: string;
  category?: string;
  accessibility_score?: number;
  weather_risk_score?: number;
  mobility_feasibility_score?: number;
  verified_facts?: string[];
  unknown_facts?: string[];
}

export interface RagRequest {
  model_name?: string | null;
  user_profile?: Record<string, unknown>;
  weather_summary?: Record<string, unknown>;
  candidate_places: RagCandidatePlace[];
  airport_context?: Record<string, unknown>;
}

export interface RagResponse {
  summary: string;
  recommended_itinerary_reason: string;
  risk_explanation: string;
  airport_guidance: string;
  cautions: string[];
  source: string;
}

export interface RetrievedDocument {
  score: number;
  doc_id: string;
  place_id: string | null;
  place_name: string | null;
  lat: number | null;
  lng: number | null;
  category: string | null;
  risk_level: string | null;
  text: string;
  source_type: string | null;
  source_file: string | null;
  image_file: string | null;
  source: string | null;
}

export interface RagAskRequest {
  question: string;
  place_name?: string | null;
  category?: string | null;
  top_k?: number;
}

export interface RagAskResponse {
  question: string;
  retrieved_documents: RetrievedDocument[];
}
