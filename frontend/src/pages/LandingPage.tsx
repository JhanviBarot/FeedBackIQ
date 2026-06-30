import { Link } from 'react-router-dom';
import { BarChart3, ArrowRight, PlayCircle, Zap, TrendingUp, Shield, Users, Star, Sparkles } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white overflow-hidden">
      {/* Background decorations */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-primary/10 rounded-full blur-3xl translate-y-1/4 -translate-x-1/4" />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 glass z-50 border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-primary font-bold text-xl group">
            <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <span className="gradient-text">FeedbackIQ</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to="/login"
              className="text-gray-600 hover:text-primary font-medium transition-colors px-4 py-2"
            >
              Log in
            </Link>
            <Link
              to="/signup"
              className="group gradient-bg text-white font-medium rounded-xl px-6 py-2.5 shadow-lg hover:shadow-xl transition-all hover:scale-105"
            >
              <span className="flex items-center gap-2">
                Get Started
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </span>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left content */}
            <div className="text-center lg:text-left">
              <div className="inline-flex items-center gap-2 bg-primary/10 text-primary text-sm font-medium px-4 py-2 rounded-full mb-6">
                <Sparkles className="w-4 h-4" />
                AI-Powered Customer Intelligence
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-6">
                Turn Customer Feedback Into{' '}
                <span className="relative">
                  <span className="gradient-text">Action</span>
                  <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" fill="none">
                    <path d="M2 10C50 6 100 6 150 8C200 10 250 6 298 10" stroke="#0F6E56" strokeWidth="3" strokeLinecap="round"/>
                  </svg>
                </span>
              </h1>
              <p className="text-xl text-gray-600 mb-6 leading-relaxed">
                FeedbackIQ analyzes thousands of reviews in minutes, not months.
                Get sentiment analysis, identify critical issues, and generate
                actionable recommendations automatically.
              </p>
              <p className="text-sm text-muted mb-10 leading-relaxed">
                Built for E-commerce, SaaS, Hospitality, Retail, and Logistics —
                with tailored AI recommendations for each.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
                <Link
                  to="/signup"
                  className="group gradient-bg text-white font-semibold rounded-2xl px-8 py-4 text-lg shadow-xl hover:shadow-2xl transition-all hover:scale-105 pulse-glow"
                >
                  <span className="flex items-center gap-2">
                    Get Started Free
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </span>
                </Link>
                <button className="group flex items-center gap-2 text-gray-600 hover:text-primary font-medium px-6 py-4 text-lg transition-colors">
                  <div className="w-12 h-12 rounded-full bg-gray-100 group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                    <PlayCircle className="w-6 h-6" />
                  </div>
                  See How It Works
                </button>
              </div>

              {/* Trust badges */}
              <div className="mt-12 flex items-center justify-center lg:justify-start gap-6">
                <div className="flex -space-x-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="w-10 h-10 rounded-full border-2 border-white shadow-md flex items-center justify-center text-xs font-bold"
                      style={{
                        background: `linear-gradient(135deg, hsl(${160 + i * 20}, 70%, ${50 + i * 5}%), hsl(${160 + i * 20}, 50%, 40%))`,
                        color: 'white',
                      }}
                    >
                      {String.fromCharCode(65 + i)}
                    </div>
                  ))}
                </div>
                <div>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  <p className="text-sm text-muted">Loved by 500+ teams</p>
                </div>
              </div>
            </div>

            {/* Right - Hero image/illustration */}
            <div className="relative hidden lg:block">
              <div className="relative z-10 float">
                {/* Main card */}
                <div className="bg-white rounded-3xl shadow-2xl p-6 border border-gray-100">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-400" />
                      <div className="w-3 h-3 rounded-full bg-yellow-400" />
                      <div className="w-3 h-3 rounded-full bg-green-400" />
                    </div>
                    <span className="text-xs text-muted">Analysis Dashboard</span>
                  </div>

                  {/* Mock dashboard content */}
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { label: 'Reviews', value: '12.5K', color: 'bg-primary/10 text-primary' },
                        { label: 'Positive', value: '72%', color: 'bg-green-100 text-green-600' },
                        { label: 'Issues', value: '23', color: 'bg-red-100 text-red-500' },
                      ].map((stat) => (
                        <div key={stat.label} className={`${stat.color} rounded-xl p-3 text-center`}>
                          <p className="text-2xl font-bold">{stat.value}</p>
                          <p className="text-xs opacity-70">{stat.label}</p>
                        </div>
                      ))}
                    </div>

                    {/* Mock chart */}
                    <div className="bg-gray-50 rounded-xl p-4">
                      <div className="flex items-end justify-between h-24 gap-2">
                        {[40, 65, 45, 80, 55, 90, 70, 85, 60, 75].map((h, i) => (
                          <div
                            key={i}
                            className="flex-1 gradient-bg rounded-t opacity-80"
                            style={{ height: `${h}%` }}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Mock sentiment */}
                    <div className="flex items-center gap-3 p-3 bg-primary/5 rounded-xl">
                      <div className="w-10 h-10 rounded-full gradient-bg flex items-center justify-center">
                        <Zap className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800">AI Insight</p>
                        <p className="text-xs text-muted">Shipping delays mentioned 340 times</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Floating elements */}
                <div className="absolute -top-6 -right-6 bg-white rounded-2xl shadow-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                      <TrendingUp className="w-4 h-4 text-green-600" />
                    </div>
                    <div>
                      <p className="text-xs text-muted">Score improved</p>
                      <p className="text-sm font-bold text-green-600">+12%</p>
                    </div>
                  </div>
                </div>

                <div className="absolute -bottom-4 -left-8 bg-white rounded-2xl shadow-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-2">
                    <Shield className="w-8 h-8 text-primary" />
                    <div>
                      <p className="text-xs text-muted">Critical issues</p>
                      <p className="text-sm font-bold text-primary">3 resolved</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6 bg-gradient-to-b from-white to-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="inline-block bg-primary/10 text-primary text-sm font-semibold px-4 py-1.5 rounded-full mb-4">
              FEATURES
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Everything you need to{' '}
              <span className="gradient-text">understand your customers</span>
            </h2>
            <p className="text-muted text-lg max-w-2xl mx-auto">
              From raw feedback to strategic insights in minutes
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: TrendingUp,
                title: 'Sentiment Analysis',
                desc: 'Automatically classify reviews as positive, negative, or neutral with detailed emotion detection.',
                color: 'from-blue-500 to-cyan-400',
              },
              {
                icon: Shield,
                title: 'Issue Detection',
                desc: 'Identify critical issues before they escalate with ranked recommendations.',
                color: 'from-purple-500 to-pink-400',
              },
              {
                icon: Users,
                title: 'Actionable Insights',
                desc: 'Generate AI-powered action plans with quick wins and executive summaries.',
                color: 'from-orange-500 to-yellow-400',
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="group bg-white rounded-3xl border border-gray-100 shadow-sm hover:shadow-2xl transition-all duration-300 card-hover overflow-hidden"
              >
                <div className="p-8">
                  <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform`}>
                    <feature.icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {feature.title}
                  </h3>
                  <p className="text-muted leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
                <div className={`h-1 bg-gradient-to-r ${feature.color}`} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="gradient-bg rounded-3xl p-12 text-center relative overflow-hidden">
            {/* Background decoration */}
            <div className="absolute inset-0 opacity-10">
              <div className="absolute top-0 left-0 w-40 h-40 bg-white rounded-full blur-3xl" />
              <div className="absolute bottom-0 right-0 w-60 h-60 bg-white rounded-full blur-3xl" />
            </div>

            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Ready to transform your feedback?
              </h2>
              <p className="text-white/80 text-lg mb-8 max-w-xl mx-auto">
                Join hundreds of companies making data-driven decisions
              </p>
              <Link
                to="/signup"
                className="inline-flex items-center gap-2 bg-white text-primary font-semibold rounded-2xl px-8 py-4 text-lg hover:bg-gray-100 transition-all hover:scale-105 shadow-xl"
              >
                Start Free Trial
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-gray-100 bg-gray-50">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <span className="gradient-text font-bold text-lg">FeedbackIQ</span>
          </div>
          <p className="text-muted text-sm">
            2024 FeedbackIQ. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
