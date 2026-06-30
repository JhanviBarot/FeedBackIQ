import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, Download, FileText, AlertCircle, Lightbulb,
  CheckCircle2, Clock, Zap, Activity, AlertTriangle,
} from 'lucide-react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, LabelList,
} from 'recharts';
import AppLayout from '../components/AppLayout';
import api from '../api/client';
import { getTrendContext, getBenchmarks } from '../api/dashboard';
import { getClusters } from '../api/clusters';
import type { TrendResponse, BenchmarkResponse } from '../api/dashboard';
import type { ClustersResponse } from '../api/clusters';
import type { DashboardResponse, ActionPlanResponse } from '../types/api';

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`shimmer rounded-lg ${className}`} />;
}

// ── Card wrapper (no gradient top border) ─────────────────────────────────────
function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-2xl border border-gray-200 p-6 ${className}`}>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-semibold text-gray-900 mb-5">{children}</h2>;
}

const SENTIMENT_COLORS = ['#10b981', '#ef4444', '#9ca3af'];
const TEAL = '#0F6E56';

const IMPACT_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-green-100 text-green-700',
};
const EFFORT_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-red-100 text-red-700',
};
const SENTIMENT_DOT: Record<string, string> = {
  positive: 'bg-green-500',
  negative: 'bg-red-500',
  neutral: 'bg-gray-400',
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
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const [trendData, setTrendData] = useState<TrendResponse | null>(null);
  const [trendLoading, setTrendLoading] = useState(true);

  const [benchmarkData, setBenchmarkData] = useState<BenchmarkResponse | null>(null);
  const [benchmarkLoading, setBenchmarkLoading] = useState(true);

  const [clusterData, setClusterData] = useState<ClustersResponse | null>(null);
  const [clusterLoading, setClusterLoading] = useState(true);

  // ── Data fetch ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) { navigate('/dashboard'); return; }
    api.get<DashboardResponse>(`/dashboard/${sessionId}`)
      .then((r) => {
        if (!r.data.classification_done) { navigate(`/analyse/processing?session=${sessionId}`); return; }
        setDashData(r.data);
      })
      .catch((err) => {
        const detail = err?.response?.data?.error || err?.response?.data?.detail;
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

  useEffect(() => {
    if (!sessionId) return;
    getBenchmarks(sessionId)
      .then(setBenchmarkData)
      .catch(() => setBenchmarkData({ available: false }))
      .finally(() => setBenchmarkLoading(false));
  }, [sessionId]);

  // Theme clustering — fired after the main dashboard data loads, in its own
  // request so it never blocks the core results rendering.
  useEffect(() => {
    if (!sessionId || !dashData) return;
    getClusters(sessionId)
      .then(setClusterData)
      .catch(() => setClusterData({ available: false }))
      .finally(() => setClusterLoading(false));
  }, [sessionId, dashData]);

  // ── Handlers ─────────────────────────────────────────────────────────────────
  const handleGenerateActionPlan = async () => {
    if (!sessionId) return;
    setActionPlanLoading(true);
    setActionPlanError(null);
    try {
      const { data } = await api.post<ActionPlanResponse>(`/action-plan/${sessionId}`);
      setActionPlan(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: unknown; detail?: unknown } }; message?: string };
      const detail = axiosErr?.response?.data?.error || axiosErr?.response?.data?.detail;
      setActionPlanError(typeof detail === 'string' ? detail : 'Failed to generate action plan. Please try again.');
    } finally {
      setActionPlanLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!sessionId) return;
    setDownloadingPdf(true);
    setDownloadError(null);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/report/${sessionId}`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token ?? ''}` },
      });
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.style.display = 'none';
      link.href = url;
      link.download = `feedbackiq_report_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setDownloadError(`PDF download failed: ${(err as Error).message}`);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadCsv = async () => {
    if (!sessionId) return;
    setDownloadingCsv(true);
    setDownloadError(null);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/export/${sessionId}`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${token ?? ''}` },
      });
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.style.display = 'none';
      link.href = url;
      link.download = `feedbackiq_results_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setDownloadError(`CSV download failed: ${(err as Error).message}`);
    } finally {
      setDownloadingCsv(false);
    }
  };

  // ── Error state ───────────────────────────────────────────────────────────────
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

  // ── Chart data ────────────────────────────────────────────────────────────────
  const sentimentData = dd ? [
    { name: 'Positive', value: parseFloat(dd.sentiment.positive_pct.toFixed(1)) },
    { name: 'Negative', value: parseFloat(dd.sentiment.negative_pct.toFixed(1)) },
    { name: 'Neutral',  value: parseFloat(dd.sentiment.neutral_pct.toFixed(1))  },
  ] : [];

  const emotionData = dd
    ? [...dd.emotions].sort((a, b) => b.count - a.count).slice(0, 8)
        .map((e) => ({ emotion: e.emotion, count: e.count }))
    : [];

  const categoryData = dd
    ? dd.categories.slice(0, 8).map((c) => ({ category: c.category, count: c.count, pct: c.pct }))
    : [];

  const totalUrgency = dd ? (dd.urgency.critical_count + dd.urgency.medium_count + dd.urgency.low_count) : 1;
  const criticalPct = dd ? (dd.urgency.critical_count / totalUrgency) * 100 : 0;
  const mediumPct = dd ? (dd.urgency.medium_count / totalUrgency) * 100 : 0;
  const lowPct = dd ? (dd.urgency.low_count / totalUrgency) * 100 : 0;

  const formatDate = (d: string) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  const scoreColor = (s: number) => s >= 70 ? '#27AE60' : s >= 50 ? '#F59E0B' : '#C0392B';

  // Only categories that produced at least one theme are worth showing; a
  // category that is entirely unique reviews would just add clutter.
  const themedCategories = clusterData?.available && clusterData.categories
    ? Object.entries(clusterData.categories).filter(([, c]) => c.clusters.length > 0)
    : [];

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Back nav */}
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-muted hover:text-primary text-sm transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Back to Dashboard
        </button>

        {/* SECTION 1 — Company header */}
        <Card className="flex items-start justify-between gap-4">
          <div>
            {loading ? (
              <>
                <Skeleton className="h-7 w-48 mb-2" />
                <Skeleton className="h-5 w-28" />
              </>
            ) : (
              <>
                <h1 className="text-2xl font-bold text-gray-900">{profile?.company_name || 'Analysis Results'}</h1>
                {profile?.industry && (
                  <span className="inline-block mt-1 px-3 py-0.5 bg-teal-100 text-teal-700 text-xs font-semibold rounded-full">
                    {profile.industry}
                  </span>
                )}
              </>
            )}
          </div>
          {!loading && dd && (
            <div className="text-right text-sm text-muted flex-shrink-0">
              <p className="font-medium text-gray-700">{dd.total_reviews.toLocaleString()} reviews</p>
              <p>{dashData?.created_at ? formatDate(dashData.created_at) : ''}</p>
            </div>
          )}
        </Card>

        {/* SECTION 2 — Key metrics row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {loading ? (
            [1,2,3,4].map(i => <Skeleton key={i} className="h-28" />)
          ) : dd ? (
            <>
              <div className="bg-white rounded-2xl border-b-4 border-gray-300 border border-gray-200 p-6">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Total Reviews</p>
                <p className="text-4xl font-bold text-gray-900">{dd.total_reviews.toLocaleString()}</p>
              </div>
              <div className="bg-white rounded-2xl border-b-4 border-gray-200 p-6" style={{borderBottomColor: scoreColor(dd.sentiment.overall_score)}}>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Sentiment Score</p>
                <p className="text-4xl font-bold" style={{color: scoreColor(dd.sentiment.overall_score)}}>
                  {dd.sentiment.overall_score.toFixed(0)}<span className="text-xl text-gray-400">/100</span>
                </p>
              </div>
              <div className="bg-white rounded-2xl border-b-4 border-green-400 border border-gray-200 p-6">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Positive Reviews</p>
                <p className="text-4xl font-bold text-green-600">{dd.sentiment.positive_pct.toFixed(1)}<span className="text-xl">%</span></p>
              </div>
              <div className="bg-white rounded-2xl border-b-4 border-gray-200 p-6" style={{borderBottomColor: dd.urgency.critical_count > 0 ? '#C0392B' : '#27AE60'}}>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Critical Issues</p>
                <p className="text-4xl font-bold" style={{color: dd.urgency.critical_count > 0 ? '#C0392B' : '#27AE60'}}>
                  {dd.urgency.critical_count}
                </p>
              </div>
            </>
          ) : null}
        </div>

        {/* SECTION 3 — Sentiment donut + Emotions bar (60/40 split) */}
        {!loading && dd && (
          <div className="grid md:grid-cols-5 gap-4">
            {/* Sentiment donut — 3/5 */}
            <Card className="md:col-span-3">
              <SectionTitle>Sentiment Breakdown</SectionTitle>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={sentimentData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={110}
                    dataKey="value"
                    label={({ name, value }) => `${name} ${value}%`}
                    labelLine={false}
                  >
                    {sentimentData.map((_, i) => <Cell key={i} fill={SENTIMENT_COLORS[i]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Card>

            {/* Emotions bar — 2/5 */}
            <Card className="md:col-span-2">
              <SectionTitle>Customer Emotions</SectionTitle>
              {emotionData.length === 0 ? (
                <p className="text-muted text-sm">No emotion data available.</p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={emotionData} layout="vertical" margin={{ left: 4, right: 40, top: 0, bottom: 0 }}>
                    <XAxis type="number" fontSize={11} hide />
                    <YAxis type="category" dataKey="emotion" width={80} fontSize={12} tickLine={false} axisLine={false} />
                    <Bar dataKey="count" fill={TEAL} radius={3}>
                      <LabelList dataKey="count" position="right" fontSize={12} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>
        )}

        {/* SECTION 4 — Category analysis full width */}
        {!loading && dd && (
          <Card>
            <SectionTitle>Feedback by Category</SectionTitle>
            <ResponsiveContainer width="100%" height={Math.max(280, categoryData.length * 40)}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 8, right: 60, top: 0, bottom: 0 }}>
                <XAxis type="number" fontSize={11} hide />
                <YAxis type="category" dataKey="category" width={130} fontSize={13} tickLine={false} axisLine={false} />
                <Bar dataKey="count" fill={TEAL} radius={4}>
                  <LabelList dataKey="count" position="right" fontSize={12} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {categoryData.length > 0 && (
              <p className="text-sm text-muted italic mt-3">
                {categoryData[0].category} accounts for {categoryData[0].pct.toFixed(1)}% of all feedback.
              </p>
            )}
          </Card>
        )}

        {/* SECTION 5 — Urgency stacked bar + Top issues */}
        {!loading && dd && (
          <div className="grid md:grid-cols-2 gap-4">
            {/* Urgency stacked bar */}
            <Card>
              <SectionTitle>Urgency Breakdown</SectionTitle>
              <div className="mb-4">
                <div className="h-10 w-full rounded-lg overflow-hidden flex">
                  {criticalPct > 0 && (
                    <div
                      style={{ width: `${criticalPct}%` }}
                      className="bg-red-500 transition-all"
                      title={`Critical: ${dd.urgency.critical_count}`}
                    />
                  )}
                  {mediumPct > 0 && (
                    <div
                      style={{ width: `${mediumPct}%` }}
                      className="bg-amber-400 transition-all"
                      title={`Medium: ${dd.urgency.medium_count}`}
                    />
                  )}
                  {lowPct > 0 && (
                    <div
                      style={{ width: `${lowPct}%` }}
                      className="bg-green-500 transition-all"
                      title={`Low: ${dd.urgency.low_count}`}
                    />
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm bg-red-500 flex-shrink-0" />
                  <span className="text-gray-700">Critical <strong>{dd.urgency.critical_count}</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm bg-amber-400 flex-shrink-0" />
                  <span className="text-gray-700">Medium <strong>{dd.urgency.medium_count}</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm bg-green-500 flex-shrink-0" />
                  <span className="text-gray-700">Low <strong>{dd.urgency.low_count}</strong></span>
                </div>
              </div>
            </Card>

            {/* Top issues table */}
            <Card>
              <SectionTitle>Top Negative Issues</SectionTitle>
              {dd.top_issues.length === 0 ? (
                <div className="flex flex-col items-center py-8">
                  <CheckCircle2 className="w-10 h-10 text-green-400 mb-3" />
                  <p className="text-gray-600 text-sm">No significant negative issues detected.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {dd.top_issues.slice(0, 4).map((issue, i) => (
                    <div key={i} className="flex items-start justify-between gap-3 border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-800 text-sm">{issue.category}</p>
                        <p className="text-xs text-muted mt-0.5 line-clamp-1">{issue.example}</p>
                      </div>
                      {issue.critical_count > 0 && (
                        <span className="flex-shrink-0 text-xs font-semibold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                          {issue.critical_count} critical
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

        {/* SECTION 5.5 — Theme Breakdown (within-category clustering) */}
        {clusterLoading ? (
          <Card>
            <Skeleton className="h-6 w-44 mb-3" />
            <Skeleton className="h-4 w-full max-w-xl mb-6" />
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          </Card>
        ) : themedCategories.length > 0 ? (
          <Card>
            <SectionTitle>Theme Breakdown</SectionTitle>
            <p className="text-sm text-muted -mt-3 mb-6 max-w-3xl">
              Specific patterns found within your feedback. A single category often
              contains several distinct themes — these add up to your category totals.
            </p>
            <div className="space-y-5">
              {themedCategories.map(([name, cat]) => (
                <div key={name} className="border border-gray-100 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-gray-800 mb-4">
                    {name}
                    <span className="text-muted font-normal">
                      {' '}— {cat.total} review{cat.total === 1 ? '' : 's'}
                    </span>
                  </h3>
                  <div className="space-y-3">
                    {cat.clusters.map((cl, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <span
                          className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${SENTIMENT_DOT[cl.dominant_sentiment] ?? 'bg-gray-400'}`}
                        />
                        <span className="text-sm font-bold text-gray-900 w-6 text-center flex-shrink-0">
                          {cl.count}
                        </span>
                        <span className="text-sm text-gray-500 italic line-clamp-1">
                          “{cl.theme_quote}”
                        </span>
                      </div>
                    ))}
                  </div>
                  {cat.unique.length > 0 && (
                    <p className="text-xs text-muted mt-4">
                      + {cat.unique.length} individual comment{cat.unique.length === 1 ? '' : 's'}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {/* SECTION 6 — AI Action Plan */}
        <Card>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">AI-Generated Action Plan</h2>
            {actionPlan && (
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-sm ${
                  actionPlan.health_score >= 75 ? 'bg-green-500' :
                  actionPlan.health_score >= 50 ? 'bg-amber-500' : 'bg-red-500'
                }`}>
                  {actionPlan.health_score}
                </div>
                <span className="font-semibold text-gray-700">{actionPlan.health_label}</span>
              </div>
            )}
          </div>

          {actionPlanError && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-700 text-sm font-medium">{actionPlanError}</p>
                <button onClick={handleGenerateActionPlan} className="text-red-600 text-xs underline mt-1">Try again</button>
              </div>
            </div>
          )}

          {!actionPlan && !actionPlanLoading && !actionPlanError && (
            <div className="text-center py-8">
              <Lightbulb className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm mb-4">Get AI-powered recommendations for your business</p>
              <button
                onClick={handleGenerateActionPlan}
                disabled={loading}
                className="gradient-bg text-white font-semibold rounded-xl px-6 py-3 shadow-md hover:shadow-lg transition-all disabled:opacity-50"
              >
                Generate Action Plan
              </button>
            </div>
          )}

          {actionPlanLoading && (
            <div className="text-center py-8">
              <span className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin inline-block mb-3" />
              <p className="text-muted text-sm">Generating your action plan…</p>
            </div>
          )}

          {actionPlan?.result && (
            <div className="space-y-6">
              {/* Executive summary */}
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Executive Summary</p>
                <p className="text-gray-700 text-sm leading-relaxed">{actionPlan.result.executive_summary}</p>
              </div>

              {/* Key strengths */}
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

              {/* Recommendations */}
              {actionPlan.result.recommendations.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-3">Recommendations</p>
                  <div className="space-y-3">
                    {actionPlan.result.recommendations.map((rec) => (
                      <div key={rec.rank} className="border border-gray-200 rounded-xl p-5">
                        <div className="flex items-start gap-3">
                          <span className="w-7 h-7 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                            {rec.rank}
                          </span>
                          <div className="flex-1">
                            <p className="font-semibold text-gray-800 text-sm mb-2">{rec.title}</p>
                            <div className="flex flex-wrap gap-1.5 mb-3">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${IMPACT_COLORS[rec.impact]}`}>
                                Impact: {rec.impact}
                              </span>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${EFFORT_COLORS[rec.effort]}`}>
                                Effort: {rec.effort}
                              </span>
                              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-600 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {TIMEFRAME_LABELS[rec.timeframe]}
                              </span>
                            </div>
                            <p className="text-xs text-muted italic mb-1">{rec.rationale}</p>
                            <p className="text-sm text-gray-700">{rec.action}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Win */}
              {actionPlan.result.quick_win && (
                <div className="bg-teal-50 border border-teal-200 rounded-xl p-5">
                  <p className="text-sm font-bold text-teal-700 mb-2 flex items-center gap-2">
                    ⚡ Quick Win
                  </p>
                  <p className="font-semibold text-gray-800 mb-1">{actionPlan.result.quick_win.title}</p>
                  <p className="text-sm text-gray-600 mb-2">{actionPlan.result.quick_win.description}</p>
                  <p className="text-xs font-medium text-teal-700">Expected: {actionPlan.result.quick_win.expected_outcome}</p>
                </div>
              )}
            </div>
          )}
        </Card>

        {/* SECTION 7 — Trend Analysis (only when available=true) */}
        {!trendLoading && trendData?.available && (
          <Card>
            <div className="flex items-center gap-3 mb-5">
              <Activity className="w-5 h-5 text-teal-600" />
              <SectionTitle>Trend Analysis</SectionTitle>
            </div>

            <div className="space-y-8">
              {/* Trajectory line chart */}
              {trendData.sentiment_trajectory && (
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-3">Sentiment Trajectory</p>
                  <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={trendData.sentiment_trajectory.points} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" fontSize={11} tickFormatter={(v: string) => v.slice(0, 15)} />
                      <YAxis domain={[0, 100]} fontSize={11} />
                      <Tooltip formatter={(v: number) => `${v.toFixed(1)}`} />
                      <Line type="monotone" dataKey="overall_score" stroke={TEAL} strokeWidth={2} dot={{ r: 5, fill: TEAL }} activeDot={{ r: 7 }} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex items-center gap-3 mt-3">
                    {trendData.sentiment_trajectory.trend === 'improving' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-700 rounded-full text-sm font-semibold">↑ Improving</span>
                    )}
                    {trendData.sentiment_trajectory.trend === 'declining' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-100 text-red-700 rounded-full text-sm font-semibold">↓ Declining</span>
                    )}
                    {trendData.sentiment_trajectory.trend === 'stable' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-700 rounded-full text-sm font-semibold">→ Stable</span>
                    )}
                    <span className="text-sm text-muted">
                      {trendData.sentiment_trajectory.change >= 0 ? '+' : ''}{trendData.sentiment_trajectory.change.toFixed(1)} points since first analysis
                    </span>
                  </div>
                </div>
              )}

              {/* Category Drift — FIXED arrow logic */}
              {trendData.category_drift && (
                (trendData.category_drift.growing.length > 0 || trendData.category_drift.shrinking.length > 0) && (
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-3">Category Drift</p>
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* Growing Issues: red up arrow */}
                      <div>
                        <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Growing Issues</p>
                        {trendData.category_drift.growing.length === 0 ? (
                          <p className="text-muted text-sm">None</p>
                        ) : (
                          <div className="space-y-1.5">
                            {trendData.category_drift.growing.map((item) => (
                              <div key={item.category} className="flex items-center justify-between bg-red-50 rounded-lg px-3 py-2">
                                <span className="text-sm font-medium text-gray-800">{item.category}</span>
                                <span className="text-sm text-red-600 font-semibold">↑ {item.change.toFixed(1)}% more complaints</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      {/* Improving Areas: shrinking = green down arrow */}
                      <div>
                        <p className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">Improving Areas</p>
                        {trendData.category_drift.shrinking.length === 0 ? (
                          <p className="text-muted text-sm">None</p>
                        ) : (
                          <div className="space-y-1.5">
                            {trendData.category_drift.shrinking.map((item) => (
                              <div key={item.category} className="flex items-center justify-between bg-green-50 rounded-lg px-3 py-2">
                                <span className="text-sm font-medium text-gray-800">{item.category}</span>
                                <span className="text-sm text-green-600 font-semibold">↓ {Math.abs(item.change).toFixed(1)}% fewer complaints</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              )}

              {/* Emerging Issues */}
              {trendData.emerging_issues && (
                trendData.emerging_issues.emerging.length > 0 || trendData.emerging_issues.resolved.length > 0
              ) ? (
                <div className="space-y-3">
                  {trendData.emerging_issues?.emerging.length > 0 && (
                    <div className="border border-red-200 rounded-xl p-4 bg-red-50">
                      <p className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4" /> New Critical Issues
                      </p>
                      {trendData.emerging_issues.emerging.map((iss) => (
                        <div key={iss.category} className="flex items-center justify-between text-sm">
                          <span className="font-medium text-gray-800">{iss.category}</span>
                          <span className="text-red-600 font-semibold">Critical issues up by {iss.change}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {trendData.emerging_issues?.resolved.length > 0 && (
                    <div className="border border-green-200 rounded-xl p-4 bg-green-50">
                      <p className="text-sm font-semibold text-green-700 mb-2 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" /> Resolved Issues
                      </p>
                      {trendData.emerging_issues.resolved.map((iss) => (
                        <div key={iss.category} className="flex items-center justify-between text-sm">
                          <span className="font-medium text-gray-800">{iss.category}</span>
                          <span className="text-green-600 font-semibold">{iss.previous_critical} critical → 0</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </Card>
        )}

        {/* SECTION 8 — Industry Benchmarks (only when available=true) */}
        {!benchmarkLoading && benchmarkData?.available && (
          <Card>
            <SectionTitle>Industry Benchmarks</SectionTitle>
            <div className="space-y-5">
              <div className="bg-gray-50 rounded-xl px-4 py-3">
                <p className="text-sm font-semibold text-gray-700">
                  {benchmarkData.industry} Industry — {benchmarkData.company_count} companies
                </p>
              </div>

              <div className="space-y-2">
                {[
                  { label: 'Sentiment Score', yours: benchmarkData.your_score ?? 0, avg: benchmarkData.industry_avg_score ?? 0, diff: benchmarkData.score_vs_avg ?? 0, unit: '', lowerIsBetter: false },
                  { label: 'Positive Reviews', yours: benchmarkData.your_positive_pct ?? 0, avg: benchmarkData.industry_avg_positive_pct ?? 0, diff: (benchmarkData.your_positive_pct ?? 0) - (benchmarkData.industry_avg_positive_pct ?? 0), unit: '%', lowerIsBetter: false },
                  { label: 'Negative Reviews', yours: benchmarkData.your_negative_pct ?? 0, avg: benchmarkData.industry_avg_negative_pct ?? 0, diff: (benchmarkData.your_negative_pct ?? 0) - (benchmarkData.industry_avg_negative_pct ?? 0), unit: '%', lowerIsBetter: true },
                  { label: 'Critical Issues', yours: benchmarkData.your_critical_pct ?? 0, avg: benchmarkData.industry_avg_critical_pct ?? 0, diff: (benchmarkData.your_critical_pct ?? 0) - (benchmarkData.industry_avg_critical_pct ?? 0), unit: '%', lowerIsBetter: true },
                ].map((row) => {
                  const better = row.lowerIsBetter ? row.diff < -2 : row.diff > 2;
                  const worse = row.lowerIsBetter ? row.diff > 2 : row.diff < -2;
                  const badge = better ? 'bg-green-100 text-green-700' : worse ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600';
                  return (
                    <div key={row.label} className="flex items-center gap-3 border border-gray-100 rounded-xl px-4 py-3">
                      <span className="text-sm text-gray-600 w-36 flex-shrink-0">{row.label}</span>
                      <span className="text-sm font-bold text-teal-700 w-20 text-center">{row.yours.toFixed(1)}{row.unit}</span>
                      <span className="text-xs text-muted">vs</span>
                      <span className="text-sm text-gray-500 w-20 text-center">{row.avg.toFixed(1)}{row.unit} avg</span>
                      <span className={`ml-auto text-xs font-semibold px-2.5 py-1 rounded-full ${badge}`}>
                        {row.diff >= 0 ? '+' : ''}{row.diff.toFixed(1)}{row.unit}
                      </span>
                    </div>
                  );
                })}
              </div>

              {benchmarkData.score_percentile !== undefined && (
                <div className={`rounded-xl px-5 py-4 ${benchmarkData.score_percentile >= 50 ? 'bg-teal-50 border border-teal-200' : 'bg-amber-50 border border-amber-200'}`}>
                  <p className={`text-lg font-bold ${benchmarkData.score_percentile >= 50 ? 'text-teal-700' : 'text-amber-700'}`}>
                    Top {100 - benchmarkData.score_percentile}%
                  </p>
                  <p className={`text-sm ${benchmarkData.score_percentile >= 50 ? 'text-teal-600' : 'text-amber-600'}`}>
                    You rank in the top {100 - benchmarkData.score_percentile}% of {benchmarkData.industry} companies on FeedbackIQ
                  </p>
                </div>
              )}

              {benchmarkData.insight && (
                <div className="bg-teal-50 border border-teal-200 rounded-xl px-5 py-4">
                  <p className="text-sm text-teal-800">{benchmarkData.insight}</p>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* SECTION 9 — Download action bar */}
        {downloadError && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-red-700 text-sm">{downloadError}</p>
          </div>
        )}
        <div className="flex flex-col sm:flex-row gap-3 pt-2 pb-8">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf || loading}
            className="flex-1 flex items-center justify-center gap-3 gradient-bg text-white font-semibold rounded-xl px-6 py-4 shadow-md hover:shadow-lg transition-all disabled:opacity-50"
          >
            {downloadingPdf ? (
              <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Download className="w-5 h-5" />
            )}
            {downloadingPdf ? 'Generating PDF…' : 'Download PDF Report'}
          </button>
          <button
            onClick={handleDownloadCsv}
            disabled={downloadingCsv || loading}
            className="flex-1 flex items-center justify-center gap-3 border-2 border-gray-200 bg-white text-gray-700 font-semibold rounded-xl px-6 py-4 hover:bg-gray-50 transition-all disabled:opacity-50"
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
