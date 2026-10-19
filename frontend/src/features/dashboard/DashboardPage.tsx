import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api';
import { Interview, Plan, AnalyticsDashboard } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Code,
  Compass,
  Cpu,
  Flame,
  PlayCircle,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true);
      try {
        const [interviewsRes, planRes, analyticsRes] = await Promise.allSettled([
          api.get<Interview[]>('/interviews'),
          api.get<Plan | null>('/plans/active'),
          api.get<AnalyticsDashboard>('/analytics/dashboard'),
        ]);

        if (interviewsRes.status === 'fulfilled') {
          setInterviews(interviewsRes.value);
        }
        if (planRes.status === 'fulfilled') {
          setPlan(planRes.value);
        }
        if (analyticsRes.status === 'fulfilled') {
          setAnalytics(analyticsRes.value);
        }
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

  const handleToggleTask = async (taskId: string, currentCompleted: boolean) => {
    if (!plan) return;
    const newCompleted = !currentCompleted;

    setPlan({
      ...plan,
      tasks: plan.tasks.map((t) =>
        t.id === taskId
          ? {
              ...t,
              is_completed: newCompleted,
              completed_at: newCompleted ? new Date().toISOString() : undefined,
            }
          : t
      ),
    });

    try {
      await api.post(`/plans/tasks/${taskId}/toggle`, { is_completed: newCompleted });
    } catch (e) {
      // revert
      setPlan({
        ...plan,
        tasks: plan.tasks.map((t) =>
          t.id === taskId ? { ...t, is_completed: currentCompleted } : t
        ),
      });
    }
  };

  const todaysTasks = plan
    ? plan.tasks.filter((t) => t.day_number === (plan.current_day || 1))
    : [];

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-ink-muted">Loading your cockpit dashboard...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Brand Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-white border border-surface-border p-6 sm:p-10">
        <div className="absolute top-0 right-0 -mt-6 -mr-6 w-72 h-72 rounded-full bg-lime-500/10 blur-3xl pointer-events-none" />

        <div className="max-w-2xl relative z-10 space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant="lime" className="gap-1 font-mono uppercase tracking-wider text-[11px]">
              <Sparkles className="w-3 h-3 text-lime-700" />
              Career Readiness & Rigor
            </Badge>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-ink">
            “Your interview went badly. Good. Now we have data.”
          </h1>

          <p className="text-sm sm:text-base text-ink-muted leading-relaxed">
            Welcome back, <span className="font-semibold text-ink">{user?.email}</span>. No fake praise,
            no sycophantic bots. Practice with realistic human-style interviewers, pinpoint exact
            engineering trade-offs, and measure your progress.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link to="/interviews/new">
              <Button variant="primary" size="lg" className="gap-2">
                <PlayCircle className="w-4 h-4" />
                Start Practice Interview
              </Button>
            </Link>

            <Link to="/coding">
              <Button variant="secondary" size="lg" className="gap-2">
                <Code className="w-4 h-4 text-emerald-600" />
                Coding Sandbox
              </Button>
            </Link>

            <Link to="/settings/provider">
              <Button variant="ghost" size="lg" className="gap-2">
                <Cpu className="w-4 h-4 text-ink-muted" />
                BYOC Settings
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* The 3 Core Questions Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: What Do I Need to Improve? */}
        <Card className="p-6 bg-white border border-surface-border flex flex-col justify-between hover:border-zinc-300 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase text-ink-subtle tracking-wider">
                Question 1
              </span>
              <div className="w-7 h-7 rounded-md bg-rose-50 text-rose-700 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="font-bold text-base text-ink">What do I need to improve?</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              {analytics?.recurring_weaknesses && analytics.recurring_weaknesses.length > 0 ? (
                <span>
                  Top identified blind spot: <strong className="text-ink">{analytics.recurring_weaknesses[0]}</strong>
                </span>
              ) : (
                'Evidence-based scorecards quote your exact answers, contrasting them against senior engineering rubrics.'
              )}
            </p>
          </div>

          <div className="pt-4 mt-4 border-t border-surface-border">
            {interviews.length > 0 && interviews[0].status === 'completed' ? (
              <Link
                to={`/evaluations/${interviews[0].id}`}
                className="text-xs font-semibold text-lime-700 hover:text-lime-800 inline-flex items-center gap-1 group"
              >
                Review Latest Evaluation
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            ) : (
              <Link
                to="/interviews/new"
                className="text-xs font-semibold text-lime-700 hover:text-lime-800 inline-flex items-center gap-1"
              >
                Take an interview to diagnose
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </Card>

        {/* Card 2: What Should I Do Next? */}
        <Card className="p-6 bg-white border border-surface-border flex flex-col justify-between hover:border-zinc-300 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase text-ink-subtle tracking-wider">
                Question 2
              </span>
              <div className="w-7 h-7 rounded-md bg-amber-50 text-amber-700 flex items-center justify-center">
                <Flame className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="font-bold text-base text-ink">What should I do next?</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              {plan ? (
                <span>
                  Planly Day {plan.current_day}: <strong className="text-ink">{todaysTasks.length} task(s)</strong> scheduled for today.
                </span>
              ) : (
                'Planly generates daily study roadmaps, complete with coding problems and documentation references.'
              )}
            </p>
          </div>

          <div className="pt-4 mt-4 border-t border-surface-border">
            <Link
              to="/planly"
              className="text-xs font-semibold text-lime-700 hover:text-lime-800 inline-flex items-center gap-1 group"
            >
              Open Planly Roadmap
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </Card>

        {/* Card 3: Have I Actually Improved? */}
        <Card className="p-6 bg-white border border-surface-border flex flex-col justify-between hover:border-zinc-300 transition-colors">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase text-ink-subtle tracking-wider">
                Question 3
              </span>
              <div className="w-7 h-7 rounded-md bg-lime-50 text-lime-800 flex items-center justify-center">
                <TrendingUp className="w-3.5 h-3.5" />
              </div>
            </div>
            <h3 className="font-bold text-base text-ink">Have I actually improved?</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              {analytics?.reassessments && analytics.reassessments.length > 0 ? (
                <span>
                  Latest reassessment delta:{' '}
                  <strong className="text-emerald-700">
                    +{analytics.reassessments[0].score_delta} points
                  </strong>{' '}
                  on identical rubrics.
                </span>
              ) : (
                'Take reassessments after completing your study plan to measure verified score gains.'
              )}
            </p>
          </div>

          <div className="pt-4 mt-4 border-t border-surface-border">
            <Link
              to="/progress"
              className="text-xs font-semibold text-lime-700 hover:text-lime-800 inline-flex items-center gap-1 group"
            >
              View Progress Trends
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </Card>
      </div>

      {/* Main 2-Column Section: Active Daily Plan + Recent Interviews */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column (2 cols): Today's Tasks in Planly */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Flame className="w-5 h-5 text-amber-600" />
              <h2 className="text-lg font-bold tracking-tight text-ink">
                Today&apos;s Planly Schedule
              </h2>
            </div>
            {plan && (
              <Link to="/planly" className="text-xs text-lime-700 hover:text-lime-800 font-semibold">
                Full Roadmap ({plan.total_days} days) →
              </Link>
            )}
          </div>

          {!plan ? (
            <Card className="p-8 text-center bg-white border border-surface-border">
              <p className="text-sm text-ink-muted mb-2">No active improvement plan right now.</p>
              <p className="text-xs text-ink-subtle max-w-sm mx-auto mb-4">
                Finish a mock interview to have Planly generate a tailored multi-day practice syllabus.
              </p>
              <Link to="/interviews/new">
                <Button variant="primary" size="sm">Start Practice</Button>
              </Link>
            </Card>
          ) : todaysTasks.length === 0 ? (
            <Card className="p-8 text-center bg-white border border-surface-border">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <h4 className="text-sm font-semibold text-ink">Day {plan.current_day} Complete!</h4>
              <p className="text-xs text-ink-muted mt-1">
                You have finished all tasks scheduled for today. Rest up or advance to Day {plan.current_day + 1}.
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {todaysTasks.map((task) => (
                <Card
                  key={task.id}
                  className={`p-4 transition-all border ${
                    task.is_completed
                      ? 'bg-white/80 border-surface-border opacity-70'
                      : 'bg-white border-surface-border hover:border-zinc-300'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <button
                      onClick={() => handleToggleTask(task.id, task.is_completed)}
                      className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                        task.is_completed
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-zinc-300 hover:border-lime-500 bg-white'
                      }`}
                    >
                      {task.is_completed && <CheckCircle2 className="w-3.5 h-3.5" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`text-sm font-semibold text-ink truncate ${
                            task.is_completed ? 'line-through text-ink-muted' : ''
                          }`}
                        >
                          {task.title}
                        </span>
                        <span className="text-[11px] text-ink-muted font-mono flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {task.estimated_minutes}m
                        </span>
                      </div>
                      <p className="text-xs text-ink-muted mt-1 line-clamp-2">{task.description}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Right Column (1 col): Recent Practice Sessions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold tracking-tight text-ink flex items-center gap-2">
              <Compass className="w-5 h-5 text-lime-600" />
              Recent Interviews
            </h2>
            <Link to="/interviews/new" className="text-xs text-lime-700 hover:text-lime-800 font-semibold">
              + New
            </Link>
          </div>

          {interviews.length === 0 ? (
            <Card className="p-6 text-center bg-white border border-surface-border">
              <p className="text-xs text-ink-muted mb-3">No interview sessions recorded yet.</p>
              <Link to="/interviews/new">
                <Button variant="primary" size="sm">Launch First Session</Button>
              </Link>
            </Card>
          ) : (
            <div className="space-y-3">
              {interviews.slice(0, 5).map((interview) => (
                <Card
                  key={interview.id}
                  className="p-4 bg-white border border-surface-border hover:border-zinc-300 transition-all space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className="text-xs font-bold text-ink truncate">{interview.title}</h4>
                      <p className="text-[11px] text-ink-muted mt-0.5">
                        {interview.category} • {interview.target_role}
                      </p>
                    </div>
                    <Badge
                      variant={
                        interview.status === 'completed'
                          ? 'emerald'
                          : interview.status === 'in_progress'
                          ? 'lime'
                          : 'zinc'
                      }
                      className="text-[10px] font-mono uppercase"
                    >
                      {interview.status}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-surface-border text-xs">
                    <span className="text-[11px] text-ink-subtle">
                      {new Date(interview.created_at).toLocaleDateString()}
                    </span>

                    {interview.status === 'completed' ? (
                      <Link
                        to={`/evaluations/${interview.id}`}
                        className="font-semibold text-lime-700 hover:text-lime-800 flex items-center gap-1 text-[11px]"
                      >
                        Scorecard →
                      </Link>
                    ) : (
                      <Link
                        to={`/interviews/${interview.id}`}
                        className="font-semibold text-lime-700 hover:text-lime-800 flex items-center gap-1 text-[11px]"
                      >
                        Resume →
                      </Link>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
