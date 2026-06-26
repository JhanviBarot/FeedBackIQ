import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, Clock, TrendingUp } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import { listSessions } from '../api/sessions';
import type { SessionSummary } from '../types/api';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listSessions()
      .then((r) => setSessions(r.sessions))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, []);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
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

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto">
        <div className="mb-8 flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl gradient-bg flex items-center justify-center shadow-lg">
            <Clock className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analysis History</h1>
            <p className="text-muted">View and manage all your past feedback analyses</p>
          </div>
        </div>

        {loading ? (
          <div className="bg-white rounded-3xl border border-gray-100 shadow-xl p-16 text-center text-muted">
            Loading…
          </div>
        ) : sessions.length === 0 ? (
          <div className="bg-white rounded-3xl border border-gray-100 shadow-xl p-16 text-center">
            <div className="w-20 h-20 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-6">
              <BarChart3 className="w-10 h-10 text-muted" />
            </div>
            <p className="text-gray-600 mb-4 text-lg">No analyses yet.</p>
            <button
              onClick={() => navigate('/analyse/profile')}
              className="text-primary hover:underline font-semibold"
            >
              Start your first analysis
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-3xl border border-gray-100 shadow-xl overflow-hidden">
            <div className="divide-y divide-gray-100">
              {sessions.map((session, index) => (
                <div
                  key={session.session_id}
                  onClick={() => navigate(`/results?session=${session.session_id}`)}
                  className="flex items-center gap-4 px-6 py-5 hover:bg-gray-50 cursor-pointer transition-all group"
                >
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    index % 3 === 0 ? 'bg-blue-100 text-blue-600' :
                    index % 3 === 1 ? 'bg-purple-100 text-purple-600' :
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
                    <div className="flex items-center justify-end gap-2 mt-1">
                      <TrendingUp className="w-4 h-4 text-muted" />
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${getScoreBg(session.overall_score)} ${getScoreColor(session.overall_score)}`}>
                        {session.overall_score}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
