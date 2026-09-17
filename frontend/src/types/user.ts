export type WheelchairType = "manual" | "electric" | "unknown";
export type WeatherSensitivity = "low" | "normal" | "high";

export interface UserProfile {
  start_location?: string;
  wheelchair_type: WheelchairType;
  has_companion: boolean;
  preferred_type: string[];
  departure_time?: string;
  weather_sensitivity: WeatherSensitivity;
  user_lat?: number | null;
  user_lon?: number | null;
}
