import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, BarChart3, TrendingUp, FileText, ExternalLink } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import { listSessions } from '../api/sessions';
import type { SessionSummary } from '../types/api';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`shimmer rounded-lg ${className}`} />;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const userData = localStorage.getItem('user_data');
  const user = userData ? JSON.parse(userData) : { full_name: 'User' };
  const firstName = user.full_name?.split(' ')[0] || 'there';

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  useEffect(() => {
    listSessions()
      .then((r) => setSessions(r.sessions))
      .catch(() => setSessions([]))
      .finally(() => setSessionsLoading(false));
  }, []);

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  const scoreColor = (s: number) => (s >= 75 ? 'text-green-600' : s >= 50 ? 'text-amber-600' : 'text-red-600');
  const scoreBg = (s: number) => (s >= 75 ? 'bg-green-100' : s >= 50 ? 'bg-amber-100' : 'bg-red-100');

  const totalReviews = sessions.reduce((sum, s) => sum + s.total_reviews, 0);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Greeting */}
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-muted text-sm mb-0.5">{greeting}</p>
            <h1 className="text-3xl font-bold text-gray-900">{firstName} 👋</h1>
          </div>
          <button
            onClick={() => navigate('/analyse/profile')}
            className="flex items-center gap-2 gradient-bg text-white font-semibold rounded-xl px-5 py-3 shadow-md hover:shadow-lg transition-all"
          >
            <Plus className="w-4 h-4" />
            New Analysis
          </button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-1">
              <BarChart3 className="w-5 h-5 text-teal-600" />
              <span className="text-sm text-gray-500">Total Analyses</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {sessionsLoading ? '…' : sessions.length}
            </p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-1">
              <FileText className="w-5 h-5 text-teal-600" />
              <span className="text-sm text-gray-500">Reviews Processed</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              {sessionsLoading ? '…' : totalReviews.toLocaleString()}
            </p>
          </div>
        </div>

        {/* Analyses table */}
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-900">Recent Analyses</h2>
          </div>

          {sessionsLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16 ml-auto" />
                  <Skeleton className="h-7 w-14 rounded-full" />
                  <Skeleton className="h-8 w-20 rounded-lg" />
                </div>
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-gray-600 font-medium mb-1">No analyses yet</p>
              <p className="text-muted text-sm mb-6">Upload your first batch of feedback to get started</p>
              <button
                onClick={() => navigate('/analyse/profile')}
                className="gradient-bg text-white font-semibold rounded-xl px-6 py-3"
              >
                Start Analysis
              </button>
            </div>
          ) : (
            <>
              {/* Table header */}
              <div className="grid grid-cols-[1fr_120px_100px_80px_100px] gap-4 px-6 py-3 bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-100">
                <span>Company</span>
                <span>Industry</span>
                <span>Date</span>
                <span className="text-right">Reviews</span>
                <span className="text-right"></span>
              </div>
              <div className="divide-y divide-gray-100">
                {sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className="grid grid-cols-[1fr_120px_100px_80px_100px] gap-4 px-6 py-4 items-center hover:bg-gray-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 text-sm truncate">{session.label}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${scoreBg(session.overall_score)} ${scoreColor(session.overall_score)}`}>
                          {session.overall_score.toFixed(0)}/100
                        </span>
                      </div>
                    </div>
                    <span className="text-sm text-gray-500 truncate">{(session as SessionSummary & { industry?: string }).industry || '—'}</span>
                    <span className="text-sm text-gray-500">{formatDate(session.created_at)}</span>
                    <span className="text-sm text-gray-700 font-medium text-right">{session.total_reviews.toLocaleString()}</span>
                    <div className="flex justify-end">
                      <button
                        onClick={() => navigate(`/results?session=${session.session_id}`)}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-teal-600 hover:text-teal-700 border border-teal-200 hover:bg-teal-50 rounded-lg px-3 py-1.5 transition-all"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        View Results
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
