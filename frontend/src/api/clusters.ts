import api from './client';

export interface ClusterTheme {
  theme_quote: string;
  count: number;
  dominant_sentiment: string;
  review_ids: number[];
}

export interface ClusterUnique {
  quote: string;
  review_id: number;
  urgency: string;
  sentiment: string;
}

export interface ClusterCategory {
  total: number;
  clusters: ClusterTheme[];
  unique: ClusterUnique[];
}

export interface ClustersResponse {
  available: boolean;
  reason?: string;
  total_reviews?: number;
  categories?: Record<string, ClusterCategory>;
}

export async function getClusters(sessionId: string): Promise<ClustersResponse> {
  const { data } = await api.get<ClustersResponse>(`/clusters/${sessionId}`);
  return data;
}
