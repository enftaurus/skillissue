import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../../lib/api';
import {
  Plan,
  PlanAdaptPreview,
  LearningBacklogItem,
  SuggestedBacklogItem,
} from '../../lib/types';
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
  Plus,
  Bookmark,
  Check,
  Trash2,
  Sparkles,
} from 'lucide-react';

export const PlanlyPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const evaluationIdParam = searchParams.get('from_evaluation');
  const actionParam = searchParams.get('action');
  const topicParam = searchParams.get('topic');

  const [activeTab, setActiveTab] = useState<'sprint' | 'backlog'>('sprint');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string>('');

  // Sprints / Schedule
  const [selectedDay, setSelectedDay] = useState<number>(1);

  // Adapt Schedule Modal
  const [isAdaptModalOpen, setIsAdaptModalOpen] = useState<boolean>(false);
  const [daysBehind, setDaysBehind] = useState<number>(1);
  const [adaptPreview, setAdaptPreview] = useState<PlanAdaptPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  // Create Custom Plan Modal
  const [isCreatePlanOpen, setIsCreatePlanOpen] = useState<boolean>(false);
  const [customTopic, setCustomTopic] = useState<string>('');
  const [customGoal, setCustomGoal] = useState<'fundamentals' | 'interview_prep' | 'mastery'>('interview_prep');
  const [customMinutes, setCustomMinutes] = useState<number>(45);
  const [customDays, setCustomDays] = useState<string[]>([
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
  ]);
  const [customLevel, setCustomLevel] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate');
  const [isCreatingPlan, setIsCreatingPlan] = useState<boolean>(false);

  // Backlog state
  const [backlogItems, setBacklogItems] = useState<LearningBacklogItem[]>([]);
  const [suggestedBacklog, setSuggestedBacklog] = useState<SuggestedBacklogItem[]>([]);
  const [backlogFilter, setBacklogFilter] = useState<string>('all');
  const [isAddBacklogOpen, setIsAddBacklogOpen] = useState<boolean>(false);
  const [newBacklogTopic, setNewBacklogTopic] = useState<string>('');
  const [newBacklogSubtopic, setNewBacklogSubtopic] = useState<string>('');
  const [newBacklogReason, setNewBacklogReason] = useState<string>('');
  const [newBacklogPriority, setNewBacklogPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [isAddingBacklog, setIsAddingBacklog] = useState<boolean>(false);
  const [importingId, setImportingId] = useState<string | null>(null);

  // Check query params for opening plan creation pre-filled
  useEffect(() => {
    if (actionParam === 'create' && topicParam) {
      setCustomTopic(topicParam);
      setIsCreatePlanOpen(true);
    }
  }, [actionParam, topicParam]);

  const loadPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      if (evaluationIdParam) {
        try {
          const generated = await api.post<Plan>(`/plans/generate/${evaluationIdParam}`);
          setPlan(generated);
          setSelectedDay(generated.current_day || 1);
          setLoading(false);
          return;
        } catch {
          // Fall back to active plan
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

  const loadBacklog = async () => {
    try {
      const items = await api.get<LearningBacklogItem[]>('/learning-backlog');
      setBacklogItems(items);
    } catch {
      // Ignore background fetch error
    }
  };

  const loadSuggestedBacklog = async (planId: string) => {
    try {
      const sugg = await api.get<SuggestedBacklogItem[]>(`/plans/${planId}/suggested-backlog`);
      setSuggestedBacklog(sugg);
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    loadPlan();
    loadBacklog();
  }, [evaluationIdParam]);

  useEffect(() => {
    if (plan?.id) {
      loadSuggestedBacklog(plan.id);
    }
  }, [plan?.id]);

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
      loadBacklog();
    } catch {
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
      setActionError('Failed to update task status.');
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
    } catch (err: any) {
      setActionError(err.message || 'Could not adapt schedule.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateCustomPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customTopic.trim()) return;
    setIsCreatingPlan(true);
    setActionError('');

    try {
      const created = await api.post<Plan>('/plans/custom', {
        topic: customTopic.trim(),
        goal: customGoal,
        daily_study_minutes: customMinutes,
        schedule_days: customDays,
        current_level: customLevel,
      });
      setPlan(created);
      setSelectedDay(1);
      setIsCreatePlanOpen(false);
      setActiveTab('sprint');
      loadBacklog();
      if (created.id) {
        loadSuggestedBacklog(created.id);
      }
    } catch (err: any) {
      setActionError(err.message || 'Failed to create customized study sprint.');
    } finally {
      setIsCreatingPlan(false);
    }
  };

  const handleImportBacklogItem = async (itemId: string) => {
    if (!plan) return;
    setImportingId(itemId);
    try {
      const updated = await api.post<Plan>(`/plans/${plan.id}/backlog-items`, {
        backlog_item_ids: [itemId],
      });
      setPlan(updated);
      loadBacklog();
      loadSuggestedBacklog(plan.id);
    } catch (err: any) {
      alert(err.message || 'Failed to import backlog item into sprint.');
    } finally {
      setImportingId(null);
    }
  };

  const handleAddBacklogItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBacklogTopic.trim()) return;
    setIsAddingBacklog(true);
    try {
      await api.post('/learning-backlog', {
        topic: newBacklogTopic.trim(),
        subtopic: newBacklogSubtopic.trim() || undefined,
        reason: newBacklogReason.trim() || 'Added manually for upcoming study review',
        priority: newBacklogPriority,
        source: 'manual',
      });
      setNewBacklogTopic('');
      setNewBacklogSubtopic('');
      setNewBacklogReason('');
      setIsAddBacklogOpen(false);
      loadBacklog();
    } catch (err: any) {
      alert(err.message || 'Failed to add topic to learning backlog.');
    } finally {
      setIsAddingBacklog(false);
    }
  };

  const handleUpdateBacklogStatus = async (itemId: string, newStatus: string) => {
    try {
      await api.patch(`/learning-backlog/${itemId}`, { status: newStatus });
      loadBacklog();
      if (plan?.id) loadSuggestedBacklog(plan.id);
    } catch (err: any) {
      alert(err.message || 'Failed to update backlog item status.');
    }
  };

  const handleDeleteBacklogItem = async (itemId: string) => {
    if (!window.confirm('Remove this topic from your learning backlog?')) return;
    try {
      await api.delete(`/learning-backlog/${itemId}`);
      loadBacklog();
      if (plan?.id) loadSuggestedBacklog(plan.id);
    } catch (err: any) {
      alert(err.message || 'Failed to delete backlog item.');
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

  const toggleDaySelection = (day: string) => {
    if (customDays.includes(day)) {
      if (customDays.length > 1) {
        setCustomDays(customDays.filter((d) => d !== day));
      }
    } else {
      setCustomDays([...customDays, day]);
    }
  };

  const filteredBacklog = backlogItems.filter((item) => {
    if (backlogFilter === 'all') return true;
    return item.status === backlogFilter;
  });

  const queuedBacklogCount = backlogItems.filter((i) => i.status === 'queued').length;

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-ink-muted">Loading Planly workspace...</p>
      </div>
    );
  }

  const completedCount = plan ? plan.tasks.filter((t) => t.is_completed).length : 0;
  const totalCount = plan ? plan.tasks.length : 0;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const days = plan
    ? Array.from(new Set(plan.tasks.map((t) => t.day_number))).sort((a, b) => a - b)
    : [];
  const tasksForSelectedDay = plan
    ? plan.tasks.filter((t) => t.day_number === selectedDay)
    : [];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-900 text-xs rounded-lg flex items-center justify-between shadow-xs">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-700 hover:text-red-900 font-semibold text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

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

      {/* Top Header & Navigation Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-xl sm:text-2xl text-ink">Planly Workspace</span>
            <Badge variant="lime" className="gap-1 font-mono uppercase tracking-wider text-[10px]">
              <Flame className="w-3 h-3 text-lime-700" />
              User-Controlled
            </Badge>
          </div>
          <p className="text-xs text-ink-muted mt-1">
            Commit to bounded study sprints or curate your persistent learning backlog.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAddBacklogOpen(true)}
            className="flex items-center gap-1.5 text-xs"
          >
            <Bookmark className="w-3.5 h-3.5" />
            <span>Add to Backlog</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreatePlanOpen(true)}
            className="flex items-center gap-1.5 text-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Study Sprint</span>
          </Button>
        </div>
      </div>

      {/* View Switcher: Active Sprint vs Learning Backlog */}
      <div className="flex items-center gap-2 border-b border-surface-border pb-2 text-xs">
        <button
          onClick={() => setActiveTab('sprint')}
          className={`px-3 py-1.5 rounded-md font-semibold transition-colors flex items-center gap-2 ${
            activeTab === 'sprint'
              ? 'bg-lime-50 text-lime-900 border border-lime-200 shadow-xs'
              : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
          }`}
        >
          <Calendar className="w-4 h-4 text-lime-700" />
          <span>Active Sprint {plan ? `(${progressPercent}%)` : ''}</span>
        </button>

        <button
          onClick={() => setActiveTab('backlog')}
          className={`px-3 py-1.5 rounded-md font-semibold transition-colors flex items-center gap-2 ${
            activeTab === 'backlog'
              ? 'bg-lime-50 text-lime-900 border border-lime-200 shadow-xs'
              : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
          }`}
        >
          <Bookmark className="w-4 h-4 text-lime-700" />
          <span>Learning Backlog ({queuedBacklogCount} queued)</span>
        </button>
      </div>

      {/* SPRINT VIEW */}
      {activeTab === 'sprint' && (
        <div className="space-y-8">
          {!plan ? (
            <Card className="p-10 text-center space-y-4">
              <div className="w-12 h-12 rounded-xl bg-lime-100 text-lime-800 flex items-center justify-center mx-auto">
                <Calendar className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-ink">No Active Study Sprint</h3>
                <p className="text-xs text-ink-muted max-w-md mx-auto mt-1">
                  Planly gives you complete control over your study schedule. Create a targeted sprint from your
                  preferred topic and available hours, or pull topics from your learning backlog.
                </p>
              </div>
              <div className="flex items-center justify-center gap-3 pt-2">
                <Button variant="primary" size="sm" onClick={() => setIsCreatePlanOpen(true)}>
                  Create Custom Sprint
                </Button>
                {queuedBacklogCount > 0 && (
                  <Button variant="outline" size="sm" onClick={() => setActiveTab('backlog')}>
                    Review Backlog ({queuedBacklogCount})
                  </Button>
                )}
              </div>
            </Card>
          ) : (
            <>
              {/* Sprint Header Summary */}
              <Card className="p-6 bg-white border border-surface-border">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
                        Active Learning Sprint
                      </span>
                      <Badge variant={plan.status === 'completed' ? 'emerald' : 'zinc'} size="sm">
                        {plan.status.toUpperCase()}
                      </Badge>
                    </div>
                    <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-ink">{plan.title}</h2>
                    <p className="text-xs text-ink-muted mt-1">
                      {plan.topic ? <span>Topic: <strong>{plan.topic}</strong> • </span> : null}
                      Commitment: <span className="font-semibold text-ink">{plan.daily_study_minutes} mins/day</span> •{' '}
                      Duration: {plan.total_days} days
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-surface-subtle p-3.5 rounded-xl border border-surface-border shrink-0">
                    <div className="text-left sm:text-right">
                      <div className="text-[11px] font-semibold text-ink-subtle uppercase">Progress</div>
                      <div className="text-xl font-bold font-mono text-ink">
                        {progressPercent}%
                        <span className="text-xs text-ink-muted font-normal ml-2 font-sans">
                          ({completedCount}/{totalCount})
                        </span>
                      </div>
                      <div className="w-32 h-1.5 bg-surface-border rounded-full overflow-hidden mt-1.5">
                        <div
                          className="h-full bg-lime-600 transition-all duration-500 rounded-full"
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    </div>

                    <div className="h-8 w-px bg-surface-border hidden sm:block" />

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsAdaptModalOpen(true)}
                      className="gap-1.5 text-xs whitespace-nowrap"
                    >
                      <RefreshCw className="w-3.5 h-3.5 text-ink-muted" />
                      Adapt Schedule
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Suggested Backlog Topics for This Sprint */}
              {suggestedBacklog.length > 0 && (
                <Card className="p-4 bg-lime-50/40 border-lime-200/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-lime-700" />
                      <h4 className="font-bold text-xs sm:text-sm text-lime-950">
                        Suggested Topics from Your Learning Backlog
                      </h4>
                    </div>
                    <span className="text-[11px] text-lime-800 hidden sm:inline">
                      Reinforces themes in your current sprint
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {suggestedBacklog.map((item) => (
                      <div
                        key={item.id}
                        className="p-3 bg-white rounded-lg border border-lime-200 flex flex-col justify-between gap-2 shadow-xs"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-xs text-ink">{item.topic}</span>
                            <Badge variant="zinc" size="sm">
                              {item.priority}
                            </Badge>
                          </div>
                          <p className="text-[11px] text-ink-muted mt-1">{item.suggested_reason}</p>
                        </div>
                        <div className="pt-2 border-t border-surface-border flex justify-end">
                          <Button
                            type="button"
                            variant="primary"
                            size="sm"
                            onClick={() => handleImportBacklogItem(item.id)}
                            isLoading={importingId === item.id}
                            className="text-[11px] py-1 px-2.5 h-auto"
                          >
                            Add to Sprint
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Roadmap Timeline & Selected Day Tasks */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
                {/* Timeline Selector */}
                <div className="lg:col-span-1 space-y-2">
                  <div className="flex items-center justify-between px-1 mb-2">
                    <h3 className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
                      Sprint Timeline
                    </h3>
                    <span className="text-xs text-ink-muted font-mono">Day {selectedDay} of {plan.total_days}</span>
                  </div>

                  <div className="space-y-1.5">
                    {days.map((day) => {
                      const dayTasks = plan.tasks.filter((t) => t.day_number === day);
                      const dayCompleted = dayTasks.length > 0 && dayTasks.every((t) => t.is_completed);
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

                {/* Day Tasks */}
                <div className="lg:col-span-3 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-semibold text-ink flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-lime-600" />
                      Day {selectedDay} Schedule
                    </h3>
                    <span className="text-xs text-ink-muted font-mono">
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

                              {task.task_type === 'coding' && (
                                <div className="pt-2">
                                  <Link to="/coding">
                                    <Button variant="secondary" size="sm" className="gap-1.5 text-xs">
                                      <Code className="w-3.5 h-3.5 text-emerald-600" />
                                      Open Coding Practice
                                    </Button>
                                  </Link>
                                </div>
                              )}

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
            </>
          )}
        </div>
      )}

      {/* LEARNING BACKLOG VIEW */}
      {activeTab === 'backlog' && (
        <div className="space-y-6">
          {/* Backlog Filter Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 flex-wrap">
              {['all', 'queued', 'planned', 'in_progress', 'completed', 'dismissed'].map((f) => (
                <button
                  key={f}
                  onClick={() => setBacklogFilter(f)}
                  className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${
                    backlogFilter === f
                      ? 'bg-lime-100 text-lime-900 border border-lime-300 font-semibold'
                      : 'bg-white text-ink-muted hover:text-ink border border-surface-border'
                  }`}
                >
                  {f.replace('_', ' ')}
                </button>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAddBacklogOpen(true)}
              className="text-xs self-start sm:self-auto"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              Add Topic
            </Button>
          </div>

          {filteredBacklog.length === 0 ? (
            <Card className="p-10 text-center space-y-3">
              <div className="w-10 h-10 rounded-xl bg-surface-subtle text-ink-muted flex items-center justify-center mx-auto">
                <Bookmark className="w-5 h-5" />
              </div>
              <h4 className="font-semibold text-sm text-ink">No Topics in this Backlog View</h4>
              <p className="text-xs text-ink-muted max-w-sm mx-auto">
                When you complete interviews, you can queue demonstrated weaknesses directly to this backlog,
                or manually record topics you want to revisit.
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-3.5">
              {filteredBacklog.map((item) => (
                <Card key={item.id} className="p-4 bg-white border border-surface-border space-y-3 shadow-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-2.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-sm text-ink">{item.topic}</span>
                      {item.subtopic && (
                        <Badge variant="zinc" size="sm">
                          {item.subtopic}
                        </Badge>
                      )}
                      <Badge
                        variant={item.priority === 'high' ? 'lime' : 'zinc'}
                        size="sm"
                        className="capitalize text-[10px]"
                      >
                        {item.priority} Priority
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          item.status === 'planned'
                            ? 'lime'
                            : item.status === 'completed'
                            ? 'emerald'
                            : 'zinc'
                        }
                        size="sm"
                        className="uppercase text-[10px]"
                      >
                        {item.status.replace('_', ' ')}
                      </Badge>
                      <span className="text-[11px] text-ink-faint">
                        Added {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  {item.reason && (
                    <p className="text-xs text-ink-muted leading-relaxed">
                      <span className="font-semibold text-ink">Diagnostic Origin: </span>
                      {item.reason}
                    </p>
                  )}

                  {item.learning_objective && (
                    <div className="p-2.5 bg-surface-subtle rounded-md text-xs text-ink-muted">
                      <span className="font-semibold text-ink">Objective: </span>
                      {item.learning_objective}
                    </div>
                  )}

                  {/* Actions on Backlog item */}
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5 pt-2 border-t border-surface-border text-xs">
                    <span className="text-[11px] text-ink-subtle">
                      Source: {item.source.replace('_', ' ')}
                    </span>

                    <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                      {plan && item.status === 'queued' && (
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={() => handleImportBacklogItem(item.id)}
                          isLoading={importingId === item.id}
                          className="text-xs py-1"
                        >
                          Import to Sprint
                        </Button>
                      )}

                      {item.status !== 'completed' && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUpdateBacklogStatus(item.id, 'completed')}
                          className="text-emerald-700 hover:text-emerald-800 text-xs"
                        >
                          <Check className="w-3.5 h-3.5 mr-1" />
                          Done
                        </Button>
                      )}

                      {item.status !== 'dismissed' && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUpdateBacklogStatus(item.id, 'dismissed')}
                          className="text-ink-muted hover:text-ink text-xs"
                        >
                          Dismiss
                        </Button>
                      )}

                      <button
                        onClick={() => handleDeleteBacklogItem(item.id)}
                        className="text-ink-subtle hover:text-red-600 p-1"
                        title="Delete from backlog"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* CREATE CUSTOM PLAN MODAL */}
      <Modal
        isOpen={isCreatePlanOpen}
        onClose={() => setIsCreatePlanOpen(false)}
        title="Create Learning Sprint"
      >
        <form onSubmit={handleCreateCustomPlan} className="space-y-4 text-xs">
          <p className="text-ink-muted leading-relaxed">
            Specify what you want to learn and your availability. The real configured AI provider will synthesize
            a sequenced, calibrated roadmap without requiring a prior interview.
          </p>

          <Input
            label="Learning Topic"
            type="text"
            required
            value={customTopic}
            onChange={(e) => setCustomTopic(e.target.value)}
            placeholder="e.g. Distributed Consensus (Raft/Paxos) or Database Indexing"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
                Sprint Goal
              </label>
              <select
                value={customGoal}
                onChange={(e: any) => setCustomGoal(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink"
              >
                <option value="interview_prep">Interview Readiness</option>
                <option value="fundamentals">Foundational Depth</option>
                <option value="mastery">Production Mastery</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
                Skill Level
              </label>
              <select
                value={customLevel}
                onChange={(e: any) => setCustomLevel(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink"
              >
                <option value="beginner">Beginner / Exploring</option>
                <option value="intermediate">Intermediate / Practicing</option>
                <option value="advanced">Advanced / Production</option>
              </select>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                Daily Study Availability
              </label>
              <span className="font-mono font-bold text-lime-700">{customMinutes} mins/day</span>
            </div>
            <input
              type="range"
              min={15}
              max={120}
              step={15}
              value={customMinutes}
              onChange={(e) => setCustomMinutes(Number(e.target.value))}
              className="w-full accent-lime-600"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Preferred Study Days
            </label>
            <div className="flex items-center gap-1.5 flex-wrap">
              {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map((d) => {
                const isSelected = customDays.includes(d);
                return (
                  <button
                    key={d}
                    type="button"
                    onClick={() => toggleDaySelection(d)}
                    className={`px-2.5 py-1 rounded text-[11px] font-mono capitalize transition-colors ${
                      isSelected
                        ? 'bg-lime-600 text-white font-semibold'
                        : 'bg-surface-subtle text-ink-muted hover:text-ink border border-surface-border'
                    }`}
                  >
                    {d.slice(0, 3)}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-surface-border">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsCreatePlanOpen(false)}
              disabled={isCreatingPlan}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isCreatingPlan}
              disabled={!customTopic.trim()}
            >
              Generate Sprint Roadmap
            </Button>
          </div>
        </form>
      </Modal>

      {/* ADD TO BACKLOG MODAL */}
      <Modal
        isOpen={isAddBacklogOpen}
        onClose={() => setIsAddBacklogOpen(false)}
        title="Add Topic to Learning Backlog"
      >
        <form onSubmit={handleAddBacklogItem} className="space-y-4 text-xs">
          <Input
            label="Topic"
            type="text"
            required
            value={newBacklogTopic}
            onChange={(e) => setNewBacklogTopic(e.target.value)}
            placeholder="e.g. Distributed Transactions (2PC / Sagas)"
          />

          <Input
            label="Subtopic (Optional)"
            type="text"
            value={newBacklogSubtopic}
            onChange={(e) => setNewBacklogSubtopic(e.target.value)}
            placeholder="e.g. Compensating transactions"
          />

          <Input
            label="Reason / Notes"
            type="text"
            value={newBacklogReason}
            onChange={(e) => setNewBacklogReason(e.target.value)}
            placeholder="e.g. Confused about rollback edge cases"
          />

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Priority
            </label>
            <select
              value={newBacklogPriority}
              onChange={(e: any) => setNewBacklogPriority(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-surface-border">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsAddBacklogOpen(false)}
              disabled={isAddingBacklog}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isAddingBacklog}
              disabled={!newBacklogTopic.trim()}
            >
              Save to Backlog
            </Button>
          </div>
        </form>
      </Modal>

      {/* ADAPT SCHEDULE MODAL */}
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
