export interface FloorMap {
  floor: string;
  image_url: string;
  description: string;
  source: string;
}

export interface AirportFacility {
  facility_name: string;
  terminal: string;
  floor: string;
  category: string;
  location_hint: string | null;
  source: string;
}

export interface JdcStore {
  store_name: string;
  location: string;
  category: string | null;
  open_time: string | null;
  close_time: string | null;
  phone: string | null;
  source: string;
  data_limit: string | null;
}

export interface AirportPlan {
  recommended_airport_arrival_time: string | null;
  reason: string;
  airport_floor_maps: FloorMap[];
  airport_facilities: AirportFacility[];
  jdc_stores: JdcStore[];
  cautions: string[];
}
