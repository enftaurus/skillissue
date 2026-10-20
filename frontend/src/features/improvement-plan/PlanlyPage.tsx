import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../../lib/api';
import { Plan, PlanAdaptPreview } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import {
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  Code,
  ExternalLink,
  Flame,
  PlayCircle,
  RefreshCw,
  Zap,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

export const PlanlyPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const evaluationIdParam = searchParams.get('from_evaluation');

  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string>('');

  // Adapt Schedule Modal
  const [isAdaptModalOpen, setIsAdaptModalOpen] = useState<boolean>(false);
  const [daysBehind, setDaysBehind] = useState<number>(1);
  const [selectedDay, setSelectedDay] = useState<number>(1);
  const [adaptPreview, setAdaptPreview] = useState<PlanAdaptPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  const loadPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      if (evaluationIdParam) {
        // Try generating or fetching plan from evaluation
        try {
          const generated = await api.post<Plan>(`/plans/generate/${evaluationIdParam}`);
          setPlan(generated);
          setSelectedDay(generated.current_day || 1);
          setLoading(false);
          return;
        } catch (e) {
          // If already exists or error, fall back to active plan
        }
      }
      const active = await api.get<Plan | null>('/plans/active');
      setPlan(active);
      if (active) {
        setSelectedDay(active.current_day || 1);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load your improvement plan.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlan();
  }, [evaluationIdParam]);

  const handleToggleTask = async (taskId: string, currentCompleted: boolean) => {
    if (!plan) return;
    const newCompleted = !currentCompleted;

    // Optimistic UI update
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
    } catch (err) {
      // Revert if API failed
      setPlan({
        ...plan,
        tasks: plan.tasks.map((t) =>
          t.id === taskId
            ? {
                ...t,
                is_completed: currentCompleted,
                completed_at: currentCompleted ? new Date().toISOString() : undefined,
              }
            : t
        ),
      });
      setActionError('Failed to update task status. Please check your network connection.');
    }
  };

  // Live preview for adaptation
  useEffect(() => {
    if (!isAdaptModalOpen || !plan) return;
    let isCancelled = false;

    const fetchPreview = async () => {
      setLoadingPreview(true);
      try {
        const preview = await api.post<PlanAdaptPreview>(`/plans/${plan.id}/adapt/preview`, {
          days_behind: Number(daysBehind) || 1,
        });
        if (!isCancelled) {
          setAdaptPreview(preview);
        }
      } catch (err) {
        console.warn('Failed to load adaptation preview', err);
      } finally {
        if (!isCancelled) {
          setLoadingPreview(false);
        }
      }
    };

    fetchPreview();
    return () => {
      isCancelled = true;
    };
  }, [isAdaptModalOpen, daysBehind, plan?.id]);

  const handleAdaptSchedule = async () => {
    if (!plan) return;
    setActionLoading(true);
    setActionError('');
    try {
      const updated = await api.post<Plan>(`/plans/${plan.id}/adapt`, {
        days_behind: Number(daysBehind),
      });
      setPlan(updated);
      setSelectedDay(updated.current_day || 1);
      setIsAdaptModalOpen(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(err.message);
      } else {
        setActionError('Could not adapt schedule.');
      }
    } finally {
      setActionLoading(false);
    }
  };

  const getTaskTypeIcon = (type: string) => {
    switch (type) {
      case 'coding':
        return <Code className="w-4 h-4 text-emerald-600" />;
      case 'practice':
        return <Zap className="w-4 h-4 text-amber-600" />;
      case 'reassessment':
        return <Flame className="w-4 h-4 text-rose-600" />;
      case 'concept':
      default:
        return <BookOpen className="w-4 h-4 text-sky-600" />;
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-ink-muted">Loading your Planly roadmap...</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="w-14 h-14 rounded-2xl bg-lime-500/10 border border-lime-500/20 text-lime-700 flex items-center justify-center mx-auto mb-4">
          <Flame className="w-7 h-7" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-ink mb-2">No Active Improvement Plan</h2>
        {error && <p className="text-xs text-rose-600 mb-4 bg-rose-50 p-2 rounded border border-rose-200">{error}</p>}
        <p className="text-sm text-ink-muted max-w-md mx-auto mb-6">
          Planly builds targeted multi-day practice schedules tailored to the exact weaknesses
          and missing concepts discovered in your mock interviews.
        </p>
        <Link to="/interviews/new">
          <Button variant="primary">Start Practice Interview</Button>
        </Link>
      </div>
    );
  }

  const completedCount = plan.tasks.filter((t) => t.is_completed).length;
  const totalCount = plan.tasks.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Group tasks by day
  const days = Array.from(new Set(plan.tasks.map((t) => t.day_number))).sort((a, b) => a - b);
  const tasksForSelectedDay = plan.tasks.filter((t) => t.day_number === selectedDay);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {actionError && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg flex items-center justify-between shadow-xs">
          <span>{actionError}</span>
          <button
            onClick={() => setActionError('')}
            className="text-amber-700 hover:text-amber-900 font-semibold text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Top Header Card */}
      <Card className="p-6 sm:p-8 bg-white border border-surface-border">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="lime" className="gap-1 font-mono uppercase tracking-wider text-[11px]">
                <Flame className="w-3 h-3 text-lime-700" />
                Planly Engine
              </Badge>
              <Badge variant={plan.status === 'completed' ? 'emerald' : 'zinc'}>
                {plan.status.toUpperCase()}
              </Badge>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink">{plan.title}</h1>
            <p className="text-sm text-ink-muted mt-1">
              Target Role: <span className="font-semibold text-ink">{plan.target_role}</span> •{' '}
              {plan.daily_study_minutes} mins/day commitment
            </p>
            {plan.target_skills && plan.target_skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {plan.target_skills.map((skill, i) => (
                  <Badge key={i} variant="zinc" className="text-xs">
                    {skill}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Quick Metrics & Adapt CTA */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-surface-subtle p-4 rounded-xl border border-surface-border">
            <div className="text-left sm:text-right">
              <div className="text-xs font-semibold text-ink-subtle uppercase">Progress</div>
              <div className="text-2xl font-bold font-mono text-ink">
                {progressPercent}%
                <span className="text-xs text-ink-muted font-normal ml-2 font-sans">
                  ({completedCount}/{totalCount} tasks)
                </span>
              </div>
              <div className="w-36 h-2 bg-surface-border rounded-full overflow-hidden mt-2">
                <div
                  className="h-full bg-lime-600 transition-all duration-500 rounded-full"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            <div className="h-10 w-px bg-surface-border hidden sm:block" />

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAdaptModalOpen(true)}
              className="gap-1.5 whitespace-nowrap"
            >
              <RefreshCw className="w-3.5 h-3.5 text-ink-muted" />
              Fell Behind? Adapt
            </Button>
          </div>
        </div>
      </Card>

      {/* Main Roadmap Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        {/* Left Column: Day Selector Tabs */}
        <div className="lg:col-span-1 space-y-2">
          <div className="flex items-center justify-between px-1 mb-2">
            <h3 className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
              Roadmap Timeline
            </h3>
            <span className="text-xs text-ink-muted font-mono">Day {selectedDay} of {plan.total_days}</span>
          </div>

          <div className="space-y-1.5">
            {days.map((day) => {
              const dayTasks = plan.tasks.filter((t) => t.day_number === day);
              const dayCompleted = dayTasks.every((t) => t.is_completed);
              const isSelected = selectedDay === day;
              const isCurrent = plan.current_day === day;

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDay(day)}
                  className={`w-full text-left px-3.5 py-3 rounded-lg border text-sm font-medium transition-all flex items-center justify-between ${
                    isSelected
                      ? 'bg-lime-50/70 border-lime-400 text-lime-950 font-semibold shadow-xs'
                      : 'bg-white border-surface-border text-ink-muted hover:border-zinc-300 hover:text-ink'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono ${
                        dayCompleted
                          ? 'bg-emerald-100 text-emerald-800'
                          : isSelected
                          ? 'bg-lime-600 text-white'
                          : 'bg-surface-subtle text-ink-muted'
                      }`}
                    >
                      {day}
                    </div>
                    <span>Day {day}</span>
                    {isCurrent && (
                      <span className="text-[10px] bg-lime-200 text-lime-900 px-1.5 py-0.5 rounded font-mono font-medium">
                        TODAY
                      </span>
                    )}
                  </div>

                  {dayCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <span className="text-xs font-mono text-ink-subtle">
                      {dayTasks.filter((t) => t.is_completed).length}/{dayTasks.length}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Tasks for selected day */}
        <div className="lg:col-span-3 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-ink flex items-center gap-2">
              <Calendar className="w-4 h-4 text-lime-600" />
              Day {selectedDay} Practice Schedule
            </h3>
            <span className="text-xs text-ink-muted">
              {tasksForSelectedDay.reduce((acc, t) => acc + t.estimated_minutes, 0)} mins total
            </span>
          </div>

          {tasksForSelectedDay.length === 0 ? (
            <Card className="p-8 text-center bg-white border border-surface-border">
              <p className="text-sm text-ink-muted">No tasks scheduled for this day.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {tasksForSelectedDay.map((task) => (
                <Card
                  key={task.id}
                  className={`p-5 transition-all border ${
                    task.is_completed
                      ? 'bg-white/80 border-surface-border opacity-75'
                      : 'bg-white border-surface-border hover:border-zinc-300 shadow-xs'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    {/* Completion Toggle */}
                    <button
                      onClick={() => handleToggleTask(task.id, task.is_completed)}
                      className={`mt-1 flex-shrink-0 w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${
                        task.is_completed
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-zinc-300 hover:border-lime-500 bg-white'
                      }`}
                      title={task.is_completed ? 'Mark uncompleted' : 'Mark completed'}
                    >
                      {task.is_completed && <CheckCircle2 className="w-3.5 h-3.5" />}
                    </button>

                    {/* Task Content */}
                    <div className="flex-1 space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="p-1 rounded bg-surface-subtle border border-surface-border">
                            {getTaskTypeIcon(task.task_type)}
                          </span>
                          <h4
                            className={`text-sm font-semibold text-ink ${
                              task.is_completed ? 'line-through text-ink-muted' : ''
                            }`}
                          >
                            {task.title}
                          </h4>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center gap-1 text-xs text-ink-muted font-mono">
                            <Clock className="w-3 h-3" />
                            {task.estimated_minutes}m
                          </span>
                          <Badge variant="zinc" className="text-[10px] uppercase font-mono">
                            {task.task_type}
                          </Badge>
                        </div>
                      </div>

                      <p className="text-xs text-ink-muted leading-relaxed">{task.description}</p>

                      {/* External Resources */}
                      {task.external_resources && task.external_resources.length > 0 && (
                        <div className="pt-2 border-t border-surface-border mt-3 space-y-1.5">
                          <span className="text-[11px] font-semibold text-ink-subtle uppercase tracking-wider block">
                            Recommended Resources:
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {task.external_resources.map((res, idx) => (
                              <a
                                key={idx}
                                href={res.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 text-xs text-lime-700 hover:text-lime-800 bg-lime-50 hover:bg-lime-100/70 px-2.5 py-1 rounded-md border border-lime-200 transition-colors"
                              >
                                <span>{res.title}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Coding CTA if task type is coding */}
                      {task.task_type === 'coding' && (
                        <div className="pt-2">
                          <Link to="/coding">
                            <Button variant="secondary" size="sm" className="gap-1.5 text-xs">
                              <Code className="w-3.5 h-3.5 text-emerald-600" />
                              Open Coding Sandbox
                            </Button>
                          </Link>
                        </div>
                      )}

                      {/* Reassessment CTA if task is reassessment */}
                      {task.task_type === 'reassessment' && (
                        <div className="pt-2">
                          <Link to="/interviews/new">
                            <Button variant="primary" size="sm" className="gap-1.5 text-xs">
                              <PlayCircle className="w-3.5 h-3.5" />
                              Launch Reassessment Interview
                            </Button>
                          </Link>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Adaptation Modal */}
      <Modal
        isOpen={isAdaptModalOpen}
        onClose={() => setIsAdaptModalOpen(false)}
        title="Adapt Improvement Schedule"
      >
        <div className="space-y-4">
          <p className="text-xs text-ink-muted leading-relaxed">
            Life happens. If you missed study sessions or got delayed by coursework, Planly can
            shift uncompleted tasks forward by your delay offset without discarding your completed progress.
          </p>

          <Input
            label="How many days behind schedule are you?"
            type="number"
            min={1}
            max={14}
            value={daysBehind}
            onChange={(e) => setDaysBehind(Math.max(1, Math.min(14, Number(e.target.value))))}
            helperText="Tasks already checked off stay intact. Unfinished milestones will advance."
          />

          {/* Adaptation Preview Card */}
          <div className="p-3 bg-surface-subtle rounded-lg border border-surface-border space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-ink">
              <span className="flex items-center gap-1.5">
                <RefreshCw className={`w-3.5 h-3.5 text-lime-700 ${loadingPreview ? 'animate-spin' : ''}`} />
                <span>Schedule Shift Preview</span>
              </span>
              {adaptPreview && (
                <span className="text-[11px] font-mono text-ink-muted">
                  +{adaptPreview.days_behind} day offset
                </span>
              )}
            </div>

            {adaptPreview ? (
              <div className="space-y-2 pt-1 text-xs">
                <div className="flex items-center gap-2 text-[11px]">
                  <Badge variant="lime" className="gap-1 font-mono">
                    <ShieldCheck className="w-3 h-3 text-lime-700" />
                    {plan ? plan.tasks.length - adaptPreview.shifted_tasks.length : 0} Finished (Preserved)
                  </Badge>
                  <Badge variant="zinc" className="font-mono">
                    {adaptPreview.shifted_tasks.length} Pending (Advancing)
                  </Badge>
                  <span className="text-[11px] font-mono text-ink-subtle ml-auto">
                    Days: {adaptPreview.current_total_days} → {adaptPreview.new_total_days}
                  </span>
                </div>

                {adaptPreview.shifted_tasks.length > 0 ? (
                  <div className="max-h-40 overflow-y-auto space-y-1.5 pt-1 pr-1">
                    {adaptPreview.shifted_tasks.map((shift) => (
                      <div
                        key={shift.task_id}
                        className="p-2 rounded bg-white border border-surface-border text-xs flex items-center justify-between gap-2"
                      >
                        <span className="font-medium text-ink truncate max-w-[200px]">
                          {shift.title}
                        </span>
                        <div className="flex items-center gap-1.5 shrink-0 font-mono text-[11px]">
                          <span className="text-ink-subtle">Day {shift.current_day}</span>
                          <ArrowRight className="w-3 h-3 text-lime-600" />
                          <span className="font-bold text-lime-700">Day {shift.new_day}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-ink-subtle italic py-1">
                    All tasks on your current roadmap have already been finished!
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-ink-subtle">Calculating preview shifts...</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-surface-border">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsAdaptModalOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleAdaptSchedule}
              isLoading={actionLoading}
            >
              Apply Schedule Shift
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
