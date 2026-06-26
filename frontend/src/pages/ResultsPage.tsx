import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  Download,
  TrendingUp,
  AlertTriangle,
  Smile,
  Lightbulb,
  BarChart3,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  Zap,
  Activity,
  ArrowUp,
  ArrowDown,
  Minus,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import AppLayout from '../components/AppLayout';
import api from '../api/client';
import { getTrendContext } from '../api/dashboard';
import type { TrendResponse } from '../api/dashboard';
import type { DashboardResponse, ActionPlanResponse } from '../types/api';

function Skeleton({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`shimmer rounded-lg ${className}`} style={style} />;
}

const SENTIMENT_COLORS = ['#10b981', '#ef4444', '#9ca3af'];
const CATEGORY_COLOR = '#0F6E56';
const EMOTION_COLOR = '#8B5CF6';

const IMPACT_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-600',
  medium: 'bg-amber-100 text-amber-600',
  low: 'bg-green-100 text-green-600',
};

const TIMEFRAME_LABELS: Record<string, string> = {
  immediate: 'Immediate',
  short_term: 'Short-term',
  long_term: 'Long-term',
};

export default function ResultsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');

  const [loading, setLoading] = useState(true);
  const [dashData, setDashData] = useState<DashboardResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [actionPlan, setActionPlan] = useState<ActionPlanResponse | null>(null);
  const [actionPlanLoading, setActionPlanLoading] = useState(false);
  const [actionPlanError, setActionPlanError] = useState<string | null>(null);

  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);

  const [trendData, setTrendData] = useState<TrendResponse | null>(null);
  const [trendLoading, setTrendLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) {
      navigate('/dashboard');
      return;
    }
    api.get<DashboardResponse>(`/dashboard/${sessionId}`)
      .then((r) => {
        if (!r.data.classification_done) {
          navigate(`/analyse/processing?session=${sessionId}`);
          return;
        }
        setDashData(r.data);
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail;
        setFetchError(typeof detail === 'string' ? detail : 'Failed to load results.');
      })
      .finally(() => setLoading(false));
  }, [sessionId, navigate]);

  useEffect(() => {
    if (!sessionId) return;
    getTrendContext(sessionId)
      .then(setTrendData)
      .catch(() => setTrendData({ available: false }))
      .finally(() => setTrendLoading(false));
  }, [sessionId]);

  const handleGenerateActionPlan = async () => {
    if (!sessionId) return;
    setActionPlanLoading(true);
    setActionPlanError(null);
    try {
      const { data } = await api.post<ActionPlanResponse>(`/dashboard/${sessionId}/action-plan`);
      setActionPlan(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = axiosErr?.response?.data?.detail;
      setActionPlanError(typeof detail === 'string' ? detail : 'Failed to generate action plan.');
    } finally {
      setActionPlanLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!sessionId) return;
    setDownloadingPdf(true);
    try {
      const { data } = await api.get(`/dashboard/${sessionId}/download/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch {
      // silently ignore — user can retry
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadCsv = async () => {
    if (!sessionId) return;
    setDownloadingCsv(true);
    try {
      const { data } = await api.get(`/dashboard/${sessionId}/download/csv`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `feedbackiq_${sessionId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // silently ignore — user can retry
    } finally {
      setDownloadingCsv(false);
    }
  };

  if (fetchError) {
    return (
      <AppLayout>
        <div className="max-w-lg mx-auto py-12 text-center">
          <div className="w-20 h-20 rounded-2xl bg-red-100 flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="w-10 h-10 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Error Loading Results</h1>
          <p className="text-muted mb-6">{fetchError}</p>
          <button onClick={() => navigate('/dashboard')} className="gradient-bg text-white font-semibold rounded-xl px-6 py-3">
            Back to Dashboard
          </button>
        </div>
      </AppLayout>
    );
  }

  const dd = dashData?.dashboard_data;
  const profile = dashData?.profile;

  const sentimentChartData = dd
    ? [
        { name: 'Positive', value: dd.sentiment.positive_pct },
        { name: 'Negative', value: dd.sentiment.negative_pct },
        { name: 'Neutral', value: dd.sentiment.neutral_pct },
      ]
    : [];

  const categoryChartData = dd
    ? dd.categories.slice(0, 8).map((c) => ({ category: c.category, count: c.count }))
    : [];

  const emotionChartData = dd
    ? dd.emotions.slice(0, 8).map((e) => ({ emotion: e.emotion, count: e.count }))
    : [];

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 text-muted hover:text-primary text-sm mb-4 transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
            Back to Dashboard
          </button>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl gradient-bg flex items-center justify-center shadow-lg">
              <BarChart3 className="w-7 h-7 text-white" />
            </div>
            <div>
              {loading ? (
                <>
                  <Skeleton className="h-7 w-40 mb-2" />
                  <Skeleton className="h-4 w-24" />
                </>
              ) : (
                <>
                  <h1 className="text-2xl font-bold text-gray-900">{profile?.company_name || 'Analysis Results'}</h1>
                  <p className="text-muted">{profile?.industry || ''}</p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
          {[
            {
              icon: FileText,
              label: 'Total Reviews',
              value: dd ? dd.total_reviews.toLocaleString() : null,
              color: 'from-blue-500 to-cyan-400',
              bg: 'bg-blue-50',
            },
            {
              icon: Smile,
              label: 'Positive Sentiment',
              value: dd ? `${dd.sentiment.positive_pct.toFixed(1)}%` : null,
              color: 'from-green-500 to-emerald-400',
              bg: 'bg-green-50',
            },
            {
              icon: AlertTriangle,
              label: 'Critical Issues',
              value: dd ? dd.urgency.critical_count.toString() : null,
              color: 'from-red-500 to-rose-400',
              bg: 'bg-red-50',
            },
            {
              icon: TrendingUp,
              label: 'Top Category',
              value: dd ? dd.top_category : null,
              color: 'from-purple-500 to-pink-400',
              bg: 'bg-purple-50',
            },
          ].map((metric) => (
            <div
              key={metric.label}
              className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl transition-all card-hover overflow-hidden"
            >
              <div className={`h-1 bg-gradient-to-r ${metric.color}`} />
              <div className="p-5">
                <div className={`w-12 h-12 rounded-xl ${metric.bg} flex items-center justify-center mb-4`}>
                  <metric.icon className="w-6 h-6 text-gray-600" />
                </div>
                <p className="text-muted text-sm mb-1">{metric.label}</p>
                {loading || !metric.value ? (
                  <Skeleton className="h-8 w-20" />
                ) : (
                  <p className="text-2xl font-bold text-gray-900 truncate">{metric.value}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-primary" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Analytics</h2>
          </div>

          {loading ? (
            <div className="grid md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-48" />)}
            </div>
          ) : (
            <div className="grid md:grid-cols-3 gap-8">
              {/* Sentiment Pie */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 text-center">Sentiment Distribution</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={sentimentChartData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                      label={({ value }) => `${value.toFixed(1)}%`}
                      labelLine={false}
                    >
                      {sentimentChartData.map((_, i) => (
                        <Cell key={i} fill={SENTIMENT_COLORS[i]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Categories Bar */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 text-center">Top Categories</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={categoryChartData} layout="vertical" margin={{ left: 8, right: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" fontSize={11} />
                    <YAxis type="category" dataKey="category" width={90} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="count" fill={CATEGORY_COLOR} radius={3} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Emotions Bar */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 text-center">Emotions Detected</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={emotionChartData} layout="vertical" margin={{ left: 8, right: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" fontSize={11} />
                    <YAxis type="category" dataKey="emotion" width={80} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="count" fill={EMOTION_COLOR} radius={3} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>

        {/* Urgency & Top Issues */}
        {!loading && dd && (
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {/* Urgency */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Urgency Breakdown</h2>
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Critical', count: dd.urgency.critical_count, color: 'bg-red-100 text-red-700 border-red-200' },
                  { label: 'Medium', count: dd.urgency.medium_count, color: 'bg-amber-100 text-amber-700 border-amber-200' },
                  { label: 'Low', count: dd.urgency.low_count, color: 'bg-green-100 text-green-700 border-green-200' },
                ].map((u) => (
                  <div key={u.label} className={`flex items-center justify-between rounded-xl px-4 py-3 border ${u.color}`}>
                    <span className="font-medium">{u.label}</span>
                    <span className="text-2xl font-bold">{u.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Issues */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-orange-500" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Top Issues</h2>
              </div>
              <div className="space-y-3">
                {dd.top_issues.slice(0, 4).map((issue, i) => (
                  <div key={i} className="border border-gray-100 rounded-xl p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-800 text-sm">{issue.category}</span>
                      <span className="text-xs text-red-500 font-medium">{issue.critical_count} critical</span>
                    </div>
                    <p className="text-xs text-muted line-clamp-2">{issue.example}</p>
                  </div>
                ))}
                {dd.top_issues.length === 0 && (
                  <p className="text-muted text-sm">No issues detected.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Action Plan */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-md">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">AI Action Plan</h2>
                <p className="text-muted text-sm">AI-powered recommendations for your business</p>
              </div>
            </div>
            {!actionPlan && (
              <button
                onClick={handleGenerateActionPlan}
                disabled={actionPlanLoading || loading}
                className="flex items-center gap-2 gradient-bg text-white font-medium rounded-xl px-6 py-3 shadow-md hover:shadow-lg transition-all disabled:opacity-50"
              >
                {actionPlanLoading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Generating…
                  </>
                ) : (
                  <>
                    <Lightbulb className="w-4 h-4" />
                    Generate Action Plan
                  </>
                )}
              </button>
            )}
          </div>

          {actionPlanError && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4">
              <p className="text-red-500 text-sm">{actionPlanError}</p>
            </div>
          )}

          {!actionPlan && !actionPlanLoading && !actionPlanError && (
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-8 text-center">
              <div className="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center mx-auto mb-4">
                <Lightbulb className="w-8 h-8 text-muted" />
              </div>
              <p className="text-gray-600">Generate an AI-powered action plan with prioritized recommendations</p>
            </div>
          )}

          {actionPlan?.result && (
            <div className="space-y-6">
              {/* Health Score */}
              <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-primary/5 to-primary/10 rounded-2xl border border-primary/10">
                <div className="w-16 h-16 rounded-xl gradient-bg flex items-center justify-center text-white text-xl font-bold shadow-md flex-shrink-0">
                  {actionPlan.result.health_score}
                </div>
                <div>
                  <p className="text-sm text-muted">Health Score</p>
                  <p className="text-lg font-bold text-gray-900">{actionPlan.result.health_label}</p>
                </div>
              </div>

              {/* Executive Summary */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Executive Summary</p>
                <p className="text-gray-600 text-sm leading-relaxed">{actionPlan.result.executive_summary}</p>
              </div>

              {/* Key Strengths */}
              {actionPlan.result.key_strengths.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-3">Key Strengths</p>
                  <div className="space-y-2">
                    {actionPlan.result.key_strengths.map((s, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-600">{s}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Win */}
              {actionPlan.result.quick_win && (
                <div className="border-2 border-primary/20 rounded-xl p-4 bg-primary/5">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-primary" />
                    <p className="text-sm font-semibold text-primary">Quick Win</p>
                  </div>
                  <p className="font-medium text-gray-800 mb-1">{actionPlan.result.quick_win.title}</p>
                  <p className="text-sm text-gray-600 mb-2">{actionPlan.result.quick_win.description}</p>
                  <p className="text-xs text-primary font-medium">Expected: {actionPlan.result.quick_win.expected_outcome}</p>
                </div>
              )}

              {/* Recommendations */}
              {actionPlan.result.recommendations.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-3">Recommendations</p>
                  <div className="space-y-3">
                    {actionPlan.result.recommendations.map((rec) => (
                      <div key={rec.rank} className="border border-gray-100 rounded-xl p-4">
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="w-6 h-6 rounded-full gradient-bg text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
                              {rec.rank}
                            </span>
                            <p className="font-semibold text-gray-800 text-sm">{rec.title}</p>
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${IMPACT_COLORS[rec.impact]}`}>
                              {rec.impact}
                            </span>
                            <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-600 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {TIMEFRAME_LABELS[rec.timeframe]}
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-muted mb-1">{rec.rationale}</p>
                        <p className="text-sm text-gray-700">{rec.action}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Trend Analysis */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-teal-100 flex items-center justify-center">
              <Activity className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Trend Analysis</h2>
              <p className="text-muted text-sm">How your feedback is changing over time</p>
            </div>
          </div>

          {trendLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : !trendData?.available ? (
            <div className="bg-teal-50 border border-teal-200 rounded-xl px-5 py-4">
              <p className="text-teal-700 text-sm">
                Trend analysis available after your second analysis. Complete another analysis to see how your feedback is changing over time.
              </p>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Sentiment Trajectory */}
              {trendData.sentiment_trajectory && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Sentiment Trajectory</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={trendData.sentiment_trajectory.points} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="label"
                        fontSize={11}
                        tickFormatter={(v: string) => v.slice(0, 15)}
                      />
                      <YAxis domain={[0, 100]} fontSize={11} />
                      <Tooltip formatter={(v: number) => `${v.toFixed(1)}`} />
                      <Line
                        type="monotone"
                        dataKey="overall_score"
                        stroke="#0F6E56"
                        strokeWidth={2}
                        dot={{ r: 5, fill: '#0F6E56' }}
                        activeDot={{ r: 7 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex items-center gap-4 mt-3">
                    {trendData.sentiment_trajectory.trend === 'improving' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-700 rounded-full text-sm font-semibold">
                        <ArrowUp className="w-4 h-4" /> Improving
                      </span>
                    )}
                    {trendData.sentiment_trajectory.trend === 'declining' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-100 text-red-700 rounded-full text-sm font-semibold">
                        <ArrowDown className="w-4 h-4" /> Declining
                      </span>
                    )}
                    {trendData.sentiment_trajectory.trend === 'stable' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-700 rounded-full text-sm font-semibold">
                        <Minus className="w-4 h-4" /> Stable
                      </span>
                    )}
                    <span className="text-sm text-muted">
                      {trendData.sentiment_trajectory.change >= 0 ? '+' : ''}
                      {trendData.sentiment_trajectory.change.toFixed(1)} points since first analysis
                    </span>
                  </div>
                </div>
              )}

              {/* Category Drift */}
              {trendData.category_drift && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Category Drift</h3>
                  {trendData.category_drift.growing.length === 0 &&
                   trendData.category_drift.shrinking.length === 0 &&
                   trendData.category_drift.new_categories.length === 0 ? (
                    <p className="text-muted text-sm">No significant category shifts detected.</p>
                  ) : (
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Growing Issues</p>
                        {trendData.category_drift.growing.length === 0 ? (
                          <p className="text-muted text-sm">None</p>
                        ) : (
                          <div className="space-y-1.5">
                            {trendData.category_drift.growing.map((item) => (
                              <div key={item.category} className="flex items-center justify-between bg-red-50 rounded-lg px-3 py-2">
                                <span className="text-sm font-medium text-gray-800">{item.category}</span>
                                <span className="flex items-center gap-1 text-sm text-red-600 font-semibold">
                                  <ArrowUp className="w-3.5 h-3.5" />
                                  +{item.change.toFixed(1)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                        {trendData.category_drift.new_categories.map((cat) => (
                          <span key={cat} className="inline-block mt-2 px-2.5 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded-full mr-1">
                            New: {cat}
                          </span>
                        ))}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">Improving Areas</p>
                        {trendData.category_drift.shrinking.length === 0 ? (
                          <p className="text-muted text-sm">None</p>
                        ) : (
                          <div className="space-y-1.5">
                            {trendData.category_drift.shrinking.map((item) => (
                              <div key={item.category} className="flex items-center justify-between bg-green-50 rounded-lg px-3 py-2">
                                <span className="text-sm font-medium text-gray-800">{item.category}</span>
                                <span className="flex items-center gap-1 text-sm text-green-600 font-semibold">
                                  <ArrowDown className="w-3.5 h-3.5" />
                                  {item.change.toFixed(1)}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Emerging Issues */}
              {trendData.emerging_issues && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Emerging Issues</h3>
                  {trendData.emerging_issues.emerging.length === 0 && trendData.emerging_issues.resolved.length === 0 ? (
                    <p className="text-muted text-sm">No new critical issues detected since last analysis.</p>
                  ) : (
                    <div className="space-y-3">
                      {trendData.emerging_issues.emerging.length > 0 && (
                        <div className="border-2 border-red-200 rounded-xl p-4 bg-red-50">
                          <p className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4" />
                            New Critical Issues
                          </p>
                          <div className="space-y-1.5">
                            {trendData.emerging_issues.emerging.map((iss) => (
                              <div key={iss.category} className="flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-800">{iss.category}</span>
                                <span className="text-sm text-red-600 font-semibold">
                                  Critical issues up by {iss.change}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {trendData.emerging_issues.resolved.length > 0 && (
                        <div className="border-2 border-green-200 rounded-xl p-4 bg-green-50">
                          <p className="text-sm font-semibold text-green-700 mb-2 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4" />
                            Resolved Issues
                          </p>
                          <div className="space-y-1.5">
                            {trendData.emerging_issues.resolved.map((iss) => (
                              <div key={iss.category} className="flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-800">{iss.category}</span>
                                <span className="text-sm text-green-600 font-semibold">
                                  {iss.previous_critical} critical → 0
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Download Buttons */}
        <div className="grid md:grid-cols-2 gap-4">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf || loading}
            className="flex items-center justify-center gap-3 border-2 border-primary/30 bg-white text-primary font-medium rounded-xl px-6 py-4 hover:bg-primary/5 hover:border-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloadingPdf ? (
              <span className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            ) : (
              <Download className="w-5 h-5" />
            )}
            {downloadingPdf ? 'Generating PDF…' : 'Download PDF Report'}
          </button>
          <button
            onClick={handleDownloadCsv}
            disabled={downloadingCsv || loading}
            className="flex items-center justify-center gap-3 border-2 border-gray-200 bg-white text-gray-700 font-medium rounded-xl px-6 py-4 hover:bg-gray-50 hover:border-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {downloadingCsv ? (
              <span className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
            ) : (
              <FileText className="w-5 h-5" />
            )}
            {downloadingCsv ? 'Exporting…' : 'Download CSV Export'}
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
