import { useNavigate } from 'react-router-dom';
import { Plus, ArrowRight, BarChart3, TrendingUp, FileText, AlertTriangle, Sparkles, Zap } from 'lucide-react';
import AppLayout from '../components/AppLayout';

// Mock data for past analyses
const mockSessions = [
  {
    session_id: 'session_1',
    label: 'TechCorp Inc.',
    created_at: '2024-01-15T10:30:00Z',
    total_reviews: 1250,
    overall_score: 78,
  },
  {
    session_id: 'session_2',
    label: 'RetailMax',
    created_at: '2024-01-10T14:20:00Z',
    total_reviews: 3400,
    overall_score: 62,
  },
  {
    session_id: 'session_3',
    label: 'HealthFirst',
    created_at: '2024-01-05T09:15:00Z',
    total_reviews: 890,
    overall_score: 85,
  },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const userData = localStorage.getItem('user_data');
  const user = userData ? JSON.parse(userData) : { full_name: 'User' };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-500';
    if (score >= 50) return 'text-amber-500';
    return 'text-red-500';
  };

  const getScoreBg = (score: number) => {
    if (score >= 75) return 'bg-green-100';
    if (score >= 50) return 'bg-amber-100';
    return 'bg-red-100';
  };

  const totalReviews = mockSessions.reduce((sum, s) => sum + s.total_reviews, 0);
  const avgScore = Math.round(mockSessions.reduce((sum, s) => sum + s.overall_score, 0) / mockSessions.length);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        {/* Welcome Section */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-2xl gradient-bg flex items-center justify-center shadow-lg">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="text-muted text-sm">Welcome back</p>
              <h1 className="text-3xl font-bold text-gray-900">Hello, {user.full_name}!</h1>
            </div>
          </div>
          <p className="text-muted text-lg ml-15">
            Ready to transform your customer feedback into actionable insights?
          </p>
        </div>

        {/* New Analysis CTA */}
        <div className="relative mb-10 overflow-hidden">
          <div className="absolute inset-0 gradient-bg opacity-95" />
          <div className="absolute inset-0">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-1/4 w-48 h-48 bg-white/5 rounded-full blur-2xl" />
          </div>
          <div className="relative p-8 md:p-10 rounded-3xl">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="text-center md:text-left">
                <div className="inline-flex items-center gap-2 bg-white/20 text-white text-sm font-medium px-3 py-1 rounded-full mb-3">
                  <Zap className="w-3.5 h-3.5" />
                  AI-Powered
                </div>
                <h2 className="text-2xl md:text-3xl font-bold text-white mb-3">
                  Start a New Analysis
                </h2>
                <p className="text-white/80 max-w-lg">
                  Upload your customer feedback and get instant insights with AI-powered
                  sentiment analysis and recommendations.
                </p>
              </div>
              <button
                onClick={() => navigate('/analyse/profile')}
                className="group flex-shrink-0 flex items-center gap-3 bg-white text-primary font-bold rounded-2xl px-8 py-4 shadow-xl hover:shadow-2xl transition-all hover:scale-105"
              >
                <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center">
                  <Plus className="w-5 h-5 text-white" />
                </div>
                <span className="text-lg">New Analysis</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
          {[
            { icon: BarChart3, label: 'Total Analyses', value: mockSessions.length, color: 'from-blue-500 to-cyan-400' },
            { icon: FileText, label: 'Reviews Processed', value: totalReviews.toLocaleString(), color: 'from-purple-500 to-pink-400' },
            { icon: TrendingUp, label: 'Avg. Score', value: `${avgScore}%`, color: 'from-green-500 to-emerald-400' },
            { icon: AlertTriangle, label: 'Issues Found', value: '47', color: 'from-orange-500 to-amber-400' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="group bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 card-hover overflow-hidden"
            >
              <div className={`h-1 bg-gradient-to-r ${stat.color}`} />
              <div className="p-5">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-md mb-4 group-hover:scale-110 transition-transform`}>
                  <stat.icon className="w-6 h-6 text-white" />
                </div>
                <p className="text-muted text-sm mb-1">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Recent Analyses */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-primary" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Recent Analyses</h2>
            </div>
            <button
              onClick={() => navigate('/history')}
              className="text-sm text-primary hover:underline font-medium flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-gray-100">
            {mockSessions.map((session, index) => (
              <div
                key={session.session_id}
                onClick={() => navigate(`/results?session=${session.session_id}`)}
                className="flex items-center gap-4 px-6 py-5 hover:bg-gray-50 cursor-pointer transition-all group"
              >
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  index === 0 ? 'bg-blue-100 text-blue-600' :
                  index === 1 ? 'bg-purple-100 text-purple-600' :
                  'bg-green-100 text-green-600'
                }`}>
                  <BarChart3 className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 truncate">{session.label}</p>
                  <p className="text-sm text-muted">{formatDate(session.created_at)}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-600">{session.total_reviews.toLocaleString()} reviews</p>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold mt-1 ${getScoreBg(session.overall_score)} ${getScoreColor(session.overall_score)}`}>
                    {session.overall_score}%
                  </span>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
