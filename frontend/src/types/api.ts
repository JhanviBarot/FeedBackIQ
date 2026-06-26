export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  email: string;
  full_name: string;
  has_profile: boolean;
}

export interface UserMeResponse {
  user_id: string;
  email: string;
  full_name: string;
  created_at: string;
  last_login: string | null;
  profile: ProfileData | null;
  session_count: number;
  has_profile: boolean;
}

export interface ProfileData {
  company_name: string;
  industry: string;
  categories: string[];
  description?: string | null;
  urgency_definition?: string | null;
}

export interface SessionSummary {
  session_id: string;
  label: string;
  created_at: string;
  total_reviews: number;
  overall_score: number;
}

export interface SessionsListResponse {
  sessions: SessionSummary[];
  total: number;
}

export interface CreateSessionResponse {
  session_id: string;
  profile: ProfileData;
  created_at: string;
  user_id?: string | null;
}

export interface PreprocessingSummary {
  input_count: number;
  final_count: number;
  noise_removed: number;
  exact_duplicates_removed: number;
  near_duplicates_removed: number;
  short_removed: number;
}

export interface AnalyseResponse {
  session_id: string;
  total_classified: number;
  total_failed: number;
  gemini_fallback_count: number;
  failed_batches: unknown[];
  preprocessing: PreprocessingSummary;
}

export interface SentimentData {
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  overall_score: number;
}

export interface CategoryItem {
  category: string;
  count: number;
  pct: number;
}

export interface UrgencyData {
  critical_count: number;
  medium_count: number;
  low_count: number;
  critical_pct: number;
}

export interface EmotionItem {
  emotion: string;
  count: number;
  pct: number;
}

export interface TopIssue {
  category: string;
  count: number;
  critical_count: number;
  example: string;
}

export interface DashboardData {
  total_reviews: number;
  sentiment: SentimentData;
  categories: CategoryItem[];
  urgency: UrgencyData;
  emotions: EmotionItem[];
  top_issues: TopIssue[];
  top_category: string;
  multi_aspect: {
    multi_aspect_count: number;
    multi_aspect_pct: number;
    single_aspect_count: number;
  };
}

export interface DashboardResponse {
  session_id: string;
  profile: ProfileData;
  dashboard_data: DashboardData;
  classification_done: boolean;
  total_classified: number;
  created_at?: string;
}

export interface Recommendation {
  rank: number;
  title: string;
  rationale: string;
  action: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  timeframe: 'immediate' | 'short_term' | 'long_term';
}

export interface ActionPlanResult {
  health_score: number;
  health_label: string;
  executive_summary: string;
  key_strengths: string[];
  recommendations: Recommendation[];
  quick_win: {
    title: string;
    description: string;
    expected_outcome: string;
  } | null;
  data_quality_note: string | null;
}

export interface ActionPlanResponse {
  session_id: string;
  success: boolean;
  result: ActionPlanResult | null;
  health_score: number;
  health_label: string;
  provider: string | null;
  error: string | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface HistoryResponse {
  sessions: SessionSummary[];
  total: number;
}
