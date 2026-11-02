import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { AdminAnalyticsResponse, TenantSummary } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import {
  ShieldAlert,
  Users,
  Award,
  Activity,
  Layers,
  Database,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  BarChart2,
} from 'lucide-react';

export const AdminAnalyticsPage: React.FC = () => {
  const [data, setData] = useState<AdminAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'real' | 'test'>('real');

  const fetchStats = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get<AdminAnalyticsResponse>('/analytics/admin/stats');
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch admin tenant telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 text-center">
        <div className="w-10 h-10 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-zinc-500 font-mono">Aggregating multi-tenant isolation analytics...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <Card className="p-8 text-center border-rose-200 bg-rose-50/50">
          <ShieldAlert className="w-12 h-12 text-rose-600 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-rose-950">Admin Analytics Restricted</h2>
          <p className="text-sm text-rose-700 mt-1">{error || 'Unable to access admin metrics.'}</p>
          <Button variant="secondary" className="mt-4" onClick={fetchStats}>
            <RefreshCw className="w-4 h-4 mr-2" /> Retry Connection
          </Button>
        </Card>
      </div>
    );
  }

  const realCohort = (data as any).real_stats || (data as any).real_cohort || {};
  const testCohort = (data as any).test_stats || (data as any).test_cohort || {};
  const activeCohort = activeTab === 'real' ? realCohort : testCohort;

  const totalUsers = activeCohort.user_count ?? activeCohort.total_users ?? 0;
  const totalInterviews = activeCohort.interviews_count ?? activeCohort.total_interviews ?? 0;
  const completedInterviews = activeCohort.completed_interviews ?? activeCohort.total_evaluations ?? 0;
  const avgScore = activeCohort.average_score ?? activeCohort.avg_overall_score ?? 0.0;
  const completionRate = activeCohort.completion_rate ?? activeCohort.avg_readiness_pct ?? 0.0;
  const estCost = activeCohort.estimated_cost_usd ?? 0.0;
  const retestsCount = activeCohort.retests_count ?? 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 bg-zinc-50/40 min-h-screen">
      {/* Top Banner & Persona */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-200 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold uppercase bg-zinc-900 text-white">
              ADMIN TELEMETRY
            </span>
            <span className="text-xs font-mono text-zinc-500">Tenant-Aware Isolation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-zinc-950 tracking-tight mt-1">
            Platform Analytics &amp; Tenant Partitioning
          </h1>
          <p className="text-sm text-zinc-600 mt-1">
            Real candidate sessions are strictly segregated from QA mock &amp; automated test suites.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={fetchStats} className="bg-white border-zinc-300">
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Refresh Telemetry
          </Button>
        </div>
      </div>

      {/* Cohort Tabs */}
      <div className="flex border-b border-zinc-200">
        <button
          onClick={() => setActiveTab('real')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'real'
              ? 'border-lime-600 text-lime-900 bg-lime-50/40'
              : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100/50'
          }`}
        >
          <Users className="w-4 h-4 text-lime-600" />
          Real Production Candidates
          <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs font-mono bg-lime-100 text-lime-800">
            {realCohort.user_count ?? realCohort.total_users ?? 0} users
          </span>
        </button>

        <button
          onClick={() => setActiveTab('test')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'test'
              ? 'border-indigo-600 text-indigo-900 bg-indigo-50/40'
              : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100/50'
          }`}
        >
          <Database className="w-4 h-4 text-indigo-600" />
          Test &amp; Sandbox Users
          <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs font-mono bg-indigo-100 text-indigo-800">
            {testCohort.user_count ?? testCohort.total_users ?? 0} users
          </span>
        </button>
      </div>

      {/* Cohort KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-zinc-200 bg-white shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Total Users</span>
            <Users className="w-4 h-4 text-zinc-400" />
          </div>
          <p className="text-2xl font-black text-zinc-950 mt-2">{totalUsers}</p>
          <p className="text-xs text-zinc-500 mt-1">
            In {activeTab === 'real' ? 'Production Tenant' : 'Sandbox Tenant'}
          </p>
        </Card>

        <Card className="p-5 border-zinc-200 bg-white shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Interviews Conducted</span>
            <Activity className="w-4 h-4 text-zinc-400" />
          </div>
          <p className="text-2xl font-black text-zinc-950 mt-2">{totalInterviews}</p>
          <p className="text-xs text-zinc-500 mt-1">
            {completedInterviews} Completed Sessions
          </p>
        </Card>

        <Card className="p-5 border-zinc-200 bg-white shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Average Score</span>
            <Award className="w-4 h-4 text-lime-600" />
          </div>
          <p className="text-2xl font-black text-lime-700 mt-2">{Number(avgScore).toFixed(1)} / 100</p>
          <p className="text-xs text-zinc-500 mt-1">
            Completion: {Number(completionRate).toFixed(1)}% • Retests: {retestsCount} • Cost: ${Number(estCost).toFixed(2)}
          </p>
        </Card>

        <Card className="p-5 border-zinc-200 bg-white shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Tenant State</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-lg font-bold text-zinc-900 mt-2">
            {activeTab === 'real' ? 'Isolated Prod' : 'Test Ephemeral'}
          </p>
          <p className="text-xs text-emerald-600 font-mono mt-1">Encrypted DB at Rest</p>
        </Card>
      </div>

      {/* Cohort Skill Dimension Breakdown & Weaknesses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 border-zinc-200 bg-white shadow-2xs">
          <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2 mb-4">
            <BarChart2 className="w-4 h-4 text-zinc-700" />
            Evaluation Dimensions ({activeTab === 'real' ? 'Real Cohort' : 'Sandbox'})
          </h2>
          <div className="space-y-3">
            {activeCohort.dimension_breakdown && Object.keys(activeCohort.dimension_breakdown).length > 0 ? (
              Object.entries(activeCohort.dimension_breakdown).map(([dim, score]) => (
                <div key={dim} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-medium text-zinc-700 capitalize">
                    <span>{dim.replace(/_/g, ' ')}</span>
                    <span className="font-mono font-bold text-zinc-900">{Number(score).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-zinc-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        Number(score) >= 75
                          ? 'bg-lime-500'
                          : Number(score) >= 50
                          ? 'bg-amber-400'
                          : 'bg-rose-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, Number(score)))}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-zinc-400 bg-zinc-50 rounded-xl border border-dashed border-zinc-200">
                Evaluation dimensions telemetry aggregated after completed candidate evaluations.
              </div>
            )}
          </div>
        </Card>

        <Card className="p-6 border-zinc-200 bg-white shadow-2xs">
          <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Top Recurring Candidate Weaknesses
          </h2>
          {activeCohort.recurring_weaknesses && activeCohort.recurring_weaknesses.length > 0 ? (
            <ul className="space-y-2.5">
              {activeCohort.recurring_weaknesses.map((weakness: string, idx: number) => (
                <li
                  key={idx}
                  className="p-3 rounded-xl bg-amber-50/60 border border-amber-200/70 text-xs font-medium text-amber-950 flex items-start gap-2.5"
                >
                  <span className="w-5 h-5 rounded-full bg-amber-200/80 text-amber-900 font-mono text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span className="leading-relaxed">{weakness}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-6 text-center text-xs text-zinc-400 bg-zinc-50 rounded-xl border border-dashed border-zinc-200">
              No recurring weaknesses logged yet for this cohort.
            </div>
          )}
        </Card>
      </div>

      {/* Tenants Table */}
      <Card className="p-6 border-zinc-200 bg-white shadow-2xs">
        <h2 className="text-base font-bold text-zinc-900 flex items-center gap-2 mb-4">
          <Layers className="w-4 h-4 text-zinc-700" />
          Active Tenants Partition Registry
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-zinc-200 text-zinc-500 font-medium">
                <th className="pb-3 font-semibold">Tenant Name</th>
                <th className="pb-3 font-semibold">Slug / ID</th>
                <th className="pb-3 font-semibold">Environment</th>
                <th className="pb-3 font-semibold text-right">Users</th>
                <th className="pb-3 font-semibold text-right">Interviews</th>
                <th className="pb-3 font-semibold text-right">Avg Score</th>
                <th className="pb-3 font-semibold text-right">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {data.tenants.map((tenant: TenantSummary) => (
                <tr key={tenant.id} className="hover:bg-zinc-50/70 transition-colors">
                  <td className="py-3 font-medium text-zinc-900">{tenant.name}</td>
                  <td className="py-3 font-mono text-zinc-500">{tenant.slug}</td>
                  <td className="py-3">
                    {tenant.is_test ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-indigo-50 text-indigo-700 border border-indigo-200">
                        Test Sandbox
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-lime-50 text-lime-800 border border-lime-200">
                        Production
                      </span>
                    )}
                  </td>
                  <td className="py-3 font-mono text-right text-zinc-800">{tenant.user_count}</td>
                  <td className="py-3 font-mono text-right text-zinc-800">{tenant.interview_count}</td>
                  <td className="py-3 font-mono text-right font-bold text-lime-700">
                    {tenant.avg_score > 0 ? `${tenant.avg_score.toFixed(1)}%` : '—'}
                  </td>
                  <td className="py-3 font-mono text-right text-zinc-400">
                    {new Date(tenant.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
