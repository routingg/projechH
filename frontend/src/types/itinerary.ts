export interface WeatherSummary {
  rain_probability: number | null;
  wind_speed: number | null;
  weather_alert: string | null;
}

export interface ItinerarySlot {
  period: string;
  time_hint: string;
  title: string;
  place_id?: string | null;
  place_name: string | null;
  category: string | null;
  lat?: number | null;
  lon?: number | null;
  reason: string;
  is_alternative: boolean;
  is_user_selected?: boolean;
}

export interface EarlyDeparture {
  recommended: boolean;
  recommended_airport_arrival_time: string | null;
  reason: string;
}

export interface Itinerary {
  travel_date: string | null;
  weather_summary: WeatherSummary;
  slots: ItinerarySlot[];
  early_departure: EarlyDeparture;
  cautions: string[];
}
