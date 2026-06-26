import api from './client';

export interface TrendPoint {
  session_id: string;
  label: string;
  created_at: string;
  overall_score: number;
  positive_pct: number;
  negative_pct: number;
}

export interface SentimentTrajectory {
  points: TrendPoint[];
  trend: 'improving' | 'declining' | 'stable' | 'insufficient_data';
  change: number;
}

export interface CategoryDriftItem {
  category: string;
  first_pct: number;
  latest_pct: number;
  change: number;
}

export interface CategoryDrift {
  growing: CategoryDriftItem[];
  shrinking: CategoryDriftItem[];
  stable: CategoryDriftItem[];
  new_categories: string[];
  dropped_categories: string[];
}

export interface EmergingIssue {
  category: string;
  previous_critical: number;
  current_critical: number;
  change: number;
}

export interface ResolvedIssue {
  category: string;
  previous_critical: number;
  current_critical: number;
}

export interface EmergingIssues {
  emerging: EmergingIssue[];
  resolved: ResolvedIssue[];
  unchanged: string[];
}

export interface TrendResponse {
  available: boolean;
  session_count?: number;
  sessions_analysed?: number;
  sentiment_trajectory?: SentimentTrajectory;
  category_drift?: CategoryDrift;
  emerging_issues?: EmergingIssues;
  generated_at?: string;
  message?: string;
  error?: string;
  session_id?: string;
}

export async function getTrendContext(sessionId: string): Promise<TrendResponse> {
  const { data } = await api.get<TrendResponse>(`/trends/${sessionId}/context`);
  return data;
}

export interface BenchmarkResponse {
  available: boolean;
  reason?: string;
  company_count?: number;
  industry?: string;
  your_score?: number;
  industry_avg_score?: number;
  score_percentile?: number;
  score_vs_avg?: number;
  your_positive_pct?: number;
  industry_avg_positive_pct?: number;
  your_negative_pct?: number;
  industry_avg_negative_pct?: number;
  your_critical_pct?: number;
  industry_avg_critical_pct?: number;
  common_top_category?: string;
  score_distribution?: Record<string, number>;
  insight?: string;
}

export async function getBenchmarks(sessionId: string): Promise<BenchmarkResponse> {
  const { data } = await api.get<BenchmarkResponse>(`/benchmarks/${sessionId}`);
  return data;
}
