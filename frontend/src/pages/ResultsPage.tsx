import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  Download,
  TrendingUp,
  AlertTriangle,
  Smile,
  AlertCircle,
  Lightbulb,
  BarChart3,
  Sparkles,
} from 'lucide-react';
import AppLayout from '../components/AppLayout';

// Skeleton component
function Skeleton({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`shimmer rounded-lg ${className}`} style={style} />;
}

// Mock data
const MOCK_DATA = {
  company_name: 'TechCorp Inc.',
  industry: 'Technology',
  total_reviews: 1250,
  sentiment: { positive_pct: 68, negative_pct: 22, neutral_pct: 10, overall_score: 72 },
  urgency: { critical_count: 23, medium_count: 45, low_count: 89 },
  top_category: 'Product Quality',
};

export default function ResultsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1500);
    return () => clearTimeout(timer);
  }, []);

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
                  <h1 className="text-2xl font-bold text-gray-900">{MOCK_DATA.company_name}</h1>
                  <p className="text-muted">{MOCK_DATA.industry}</p>
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
              value: MOCK_DATA.total_reviews.toLocaleString(),
              color: 'from-blue-500 to-cyan-400',
              bg: 'bg-blue-50',
            },
            {
              icon: Smile,
              label: 'Sentiment Score',
              value: `${MOCK_DATA.sentiment.positive_pct}%`,
              color: 'from-green-500 to-emerald-400',
              bg: 'bg-green-50',
            },
            {
              icon: AlertTriangle,
              label: 'Critical Issues',
              value: MOCK_DATA.urgency.critical_count.toString(),
              color: 'from-red-500 to-rose-400',
              bg: 'bg-red-50',
            },
            {
              icon: TrendingUp,
              label: 'Top Category',
              value: MOCK_DATA.top_category,
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
                {loading ? (
                  <Skeleton className="h-8 w-20" />
                ) : (
                  <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Analytics Charts */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-primary" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Analytics Charts</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              { title: 'Sentiment Distribution', icon: Smile, desc: 'Pie chart visualization' },
              { title: 'Top Categories', icon: TrendingUp, desc: 'Bar chart visualization' },
              { title: 'Emotions Detected', icon: AlertCircle, desc: 'Horizontal bar chart' },
            ].map((chart) => (
              <div
                key={chart.title}
                className="border-2 border-dashed border-gray-200 rounded-2xl p-8 text-center hover:border-primary/30 transition-colors"
              >
                <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                  <chart.icon className="w-8 h-8 text-muted" />
                </div>
                <p className="font-medium text-gray-700 mb-1">{chart.title}</p>
                <p className="text-xs text-muted mb-4">{chart.desc}</p>
                <div className="space-y-2">
                  {[75, 60, 50].map((w, j) => (
                    <Skeleton key={j} className="h-2 mx-auto" style={{ width: `${w}%` }} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Plan */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-md">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">AI Action Plan</h2>
                <p className="text-muted text-sm">Get AI-powered recommendations</p>
              </div>
            </div>
            <div className="relative group">
              <button
                disabled
                className="flex items-center gap-2 bg-gray-200 text-gray-400 font-medium rounded-xl px-6 py-3 cursor-not-allowed"
              >
                <Lightbulb className="w-4 h-4" />
                {'Generate AI Action Plan'}
              </button>
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-4 py-2 bg-gray-900 text-white text-xs rounded-xl opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-xl z-10">
                Connect backend to enable
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center mx-auto mb-4">
              <Lightbulb className="w-8 h-8 text-muted" />
            </div>
            <p className="text-gray-600 mb-2">Generate an AI-powered action plan with prioritized recommendations</p>
            <p className="text-xs text-muted">Requires backend connection to enable</p>
          </div>
        </div>

        {/* Download Buttons */}
        <div className="grid md:grid-cols-2 gap-4">
          {[{ icon: Download, label: 'Download PDF Report' }, { icon: FileText, label: 'Download CSV Export' }].map(
            (btn) => (
              <div key={btn.label} className="relative group">
                <button
                  disabled
                  className="w-full flex items-center justify-center gap-3 border-2 border-gray-200 bg-white text-gray-400 font-medium rounded-xl px-6 py-4 cursor-not-allowed hover:border-gray-300 transition-colors"
                >
                  <btn.icon className="w-5 h-5" />
                  {btn.label}
                </button>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-4 py-2 bg-gray-900 text-white text-xs rounded-xl opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-xl z-10">
                  Connect backend to enable
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </AppLayout>
  );
}
