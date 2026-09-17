import { client } from "./client";
import type { JdcStore } from "../types/airport";

export interface JdcStoreResponse {
  stores: JdcStore[];
  data_limitations: string[];
}

export async function getJdcStores(): Promise<JdcStoreResponse> {
  const { data } = await client.get<JdcStoreResponse>("/api/jdc/stores");
  return data;
}
