import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../../lib/api';
import {
  Plan,
  PlanAdaptPreview,
  LearningBacklogItem,
  SuggestedBacklogItem,
  PlanReschedulePreview,
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
  Download,
  LayoutGrid,
  ListFilter,
} from 'lucide-react';

export const PlanlyPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const evaluationIdParam = searchParams.get('from_evaluation');
  const actionParam = searchParams.get('action');
  const topicParam = searchParams.get('topic');

  const [activeTab, setActiveTab] = useState<'sprint' | 'backlog'>('sprint');
  const [planView, setPlanView] = useState<'timeline' | 'calendar'>('timeline');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string>('');

  // Sprints / Schedule
  const [selectedDay, setSelectedDay] = useState<number>(1);
  const [prepDays, setPrepDays] = useState<number>(7);
  const [prepMinutes, setPrepMinutes] = useState<number>(45);
  const [prepTargetDate, setPrepTargetDate] = useState<string>('');
  const [isEvalConfigOpen, setIsEvalConfigOpen] = useState<boolean>(false);

  // Adapt / Reschedule Modal State
  const [isAdaptModalOpen, setIsAdaptModalOpen] = useState<boolean>(false);
  const [daysBehind, setDaysBehind] = useState<number>(1);
  const [adaptPreview, setAdaptPreview] = useState<PlanAdaptPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  // Reschedule to Today State
  const [isRescheduleModalOpen, setIsRescheduleModalOpen] = useState<boolean>(false);
  const [reschedulePreview, setReschedulePreview] = useState<PlanReschedulePreview | null>(null);
  const [loadingReschedulePreview, setLoadingReschedulePreview] = useState<boolean>(false);
  const [rescheduleSuccessMsg, setRescheduleSuccessMsg] = useState<string>('');

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

  const [isGeneratingFromEval, setIsGeneratingFromEval] = useState<boolean>(false);

  const loadPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      if (evaluationIdParam) {
        setIsEvalConfigOpen(true);
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

  const handleGenerateFromEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!evaluationIdParam) return;
    setIsGeneratingFromEval(true);
    setActionError('');
    try {
      const generated = await api.post<Plan>(`/plans/generate/${evaluationIdParam}`, {
        total_days: prepDays,
        daily_study_minutes: prepMinutes,
        target_date: prepTargetDate ? new Date(prepTargetDate).toISOString() : undefined,
      });
      setPlan(generated);
      setSelectedDay(generated.current_day || 1);
      setIsEvalConfigOpen(false);
      setActiveTab('sprint');
      loadBacklog();
      if (generated.id) {
        loadSuggestedBacklog(generated.id);
      }
    } catch (err: any) {
      setActionError(err.message || 'Failed to generate tailored sprint from evaluation.');
    } finally {
      setIsGeneratingFromEval(false);
    }
  };

  const handleExportIcs = () => {
    if (!plan) return;
    const startDate = plan.start_date ? new Date(plan.start_date) : new Date(plan.created_at || Date.now());
    
    const icsLines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//SkillIssue//Planly Sprint//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      `X-WR-CALNAME:Planly: ${plan.title.replace(/[,;]/g, '')}`,
    ];

    plan.tasks.forEach((task) => {
      const taskDate = new Date(startDate.getTime() + (task.day_number - 1) * 86400000);
      const year = taskDate.getUTCFullYear();
      const month = String(taskDate.getUTCMonth() + 1).padStart(2, '0');
      const day = String(taskDate.getUTCDate()).padStart(2, '0');
      const dtStart = `${year}${month}${day}T090000Z`;
      const endDate = new Date(taskDate.getTime() + (task.estimated_minutes || 45) * 60000);
      const endYear = endDate.getUTCFullYear();
      const endMonth = String(endDate.getUTCMonth() + 1).padStart(2, '0');
      const endDay = String(endDate.getUTCDate()).padStart(2, '0');
      const endHour = String(endDate.getUTCHours()).padStart(2, '0');
      const endMin = String(endDate.getUTCMinutes()).padStart(2, '0');
      const dtEnd = `${endYear}${endMonth}${endDay}T${endHour}${endMin}00Z`;

      icsLines.push(
        'BEGIN:VEVENT',
        `UID:planly-${task.id}@skillissue.ai`,
        `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, '').split('.')[0]}Z`,
        `DTSTART:${dtStart}`,
        `DTEND:${dtEnd}`,
        `SUMMARY:Day ${task.day_number}: ${task.title.replace(/[,;]/g, '')}`,
        `DESCRIPTION:${(task.description || '').replace(/\n/g, '\\n').replace(/[,;]/g, '')}`,
        'STATUS:CONFIRMED',
        'END:VEVENT'
      );
    });

    icsLines.push('END:VCALENDAR');
    const icsContent = icsLines.join('\r\n');
    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${plan.title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-schedule.ics`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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

  // Live preview for Reschedule to Today
  useEffect(() => {
    if (!isRescheduleModalOpen || !plan) return;
    let isCancelled = false;

    const fetchPreview = async () => {
      setLoadingReschedulePreview(true);
      try {
        const preview = await api.post<PlanReschedulePreview>(
          `/plans/${plan.id}/reschedule-to-today/preview`,
          {}
        );
        if (!isCancelled) {
          setReschedulePreview(preview);
        }
      } catch (err: any) {
        console.warn('Failed to load reschedule preview', err);
      } finally {
        if (!isCancelled) {
          setLoadingReschedulePreview(false);
        }
      }
    };

    fetchPreview();
    return () => {
      isCancelled = true;
    };
  }, [isRescheduleModalOpen, plan?.id]);

  const handleRescheduleToToday = async () => {
    if (!plan) return;
    setActionLoading(true);
    setActionError('');
    try {
      const updated = await api.post<Plan>(`/plans/${plan.id}/reschedule-to-today`, {});
      setPlan(updated);
      setSelectedDay(updated.current_day || 1);
      setIsRescheduleModalOpen(false);
      const finishedCount = updated.tasks.filter((t) => t.is_completed).length;
      const remainingCount = updated.tasks.filter((t) => !t.is_completed).length;
      setRescheduleSuccessMsg(
        `Sprint successfully rescheduled starting today! Preserved ${finishedCount} finished tasks, remaining ${remainingCount} tasks aligned starting today.`
      );
      setTimeout(() => setRescheduleSuccessMsg(''), 7000);
    } catch (err: any) {
      setActionError(err.message || 'Could not reschedule sprint to today.');
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
        <div className="w-10 h-10 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-500">Loading Planly workspace...</p>
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
            <Badge variant="brand" className="gap-1 font-mono uppercase tracking-wider text-xs">
              <Flame className="w-3.5 h-3.5 text-indigo-600" />
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
      <div className="flex items-center gap-2 border-b border-surface-border pb-2 text-sm">
        <button
          onClick={() => setActiveTab('sprint')}
          className={`px-3.5 py-2 rounded-xl font-semibold transition-all flex items-center gap-2 ${
            activeTab === 'sprint'
              ? 'bg-indigo-50 text-indigo-900 border border-indigo-200/80 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
          }`}
        >
          <Calendar className="w-4 h-4 text-indigo-600" />
          <span>Active Sprint {plan ? `(${progressPercent}%)` : ''}</span>
        </button>

        <button
          onClick={() => setActiveTab('backlog')}
          className={`px-3.5 py-2 rounded-xl font-semibold transition-all flex items-center gap-2 ${
            activeTab === 'backlog'
              ? 'bg-indigo-50 text-indigo-900 border border-indigo-200/80 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
          }`}
        >
          <Bookmark className="w-4 h-4 text-indigo-600" />
          <span>Learning Backlog ({queuedBacklogCount} queued)</span>
        </button>
      </div>

      {rescheduleSuccessMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs sm:text-sm font-semibold flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{rescheduleSuccessMsg}</span>
          </div>
          <button
            onClick={() => setRescheduleSuccessMsg('')}
            className="text-emerald-700 hover:text-emerald-900 font-bold px-2 py-0.5 rounded hover:bg-emerald-100"
          >
            ✕
          </button>
        </div>
      )}

      {/* SPRINT VIEW */}
      {activeTab === 'sprint' && (
        <div className="space-y-8">
          {!plan ? (
            <Card className="p-10 text-center space-y-4">
              <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-200/60 flex items-center justify-center mx-auto shadow-xs">
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
                          className="h-full bg-indigo-600 transition-all duration-500 rounded-full"
                          style={{ width: `${progressPercent}%` }}
                        />
                      </div>
                    </div>

                    <div className="h-8 w-px bg-surface-border hidden sm:block" />

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setIsRescheduleModalOpen(true)}
                        className="gap-1.5 text-xs whitespace-nowrap shadow-xs"
                        title="Reschedule remaining sprint tasks starting today based on your current progress"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Reschedule to Today</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsAdaptModalOpen(true)}
                        className="gap-1.5 text-xs whitespace-nowrap text-ink-muted hover:text-ink"
                        title="Shift schedule forward by custom days behind"
                      >
                        Adapt
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Suggested Backlog Topics for This Sprint */}
              {suggestedBacklog.length > 0 && (
                <Card className="p-4 bg-indigo-50/40 border-indigo-200/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-indigo-600" />
                      <h4 className="font-bold text-xs sm:text-sm text-indigo-950">
                        Suggested Topics from Your Learning Backlog
                      </h4>
                    </div>
                    <span className="text-xs text-indigo-700 hidden sm:inline">
                      Reinforces themes in your current sprint
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {suggestedBacklog.map((item) => (
                      <div
                        key={item.id}
                        className="p-3 bg-white rounded-lg border border-indigo-100 flex flex-col justify-between gap-2 shadow-xs"
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

              {/* Target Interview Date Countdown Banner */}
              {plan.target_date && (
                <div className="p-4 bg-lime-50/70 border border-lime-200/90 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-lime-100 text-lime-800 flex items-center justify-center font-bold text-lg">
                      🎯
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-sm text-lime-950">Target Interview Countdown</h4>
                        <Badge variant="emerald" size="sm" className="font-mono text-[10px]">
                          PACED BACKWARD
                        </Badge>
                      </div>
                      <p className="text-xs text-lime-800 mt-0.5">
                        Target Date: {new Date(plan.target_date).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })} • Pacing curriculum backward from your interview date.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    <span className="text-xs font-mono text-lime-800 font-semibold">
                      {Math.max(0, Math.ceil((new Date(plan.target_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))} days remaining
                    </span>
                  </div>
                </div>
              )}

              {/* View Switcher Bar & .ics Export */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-1.5 p-1 bg-surface-subtle rounded-xl border border-surface-border">
                  <button
                    type="button"
                    onClick={() => setPlanView('timeline')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      planView === 'timeline'
                        ? 'bg-white text-ink shadow-xs border border-surface-border'
                        : 'text-ink-muted hover:text-ink'
                    }`}
                  >
                    <ListFilter className="w-3.5 h-3.5" />
                    <span>Sprint Timeline</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlanView('calendar')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      planView === 'calendar'
                        ? 'bg-white text-ink shadow-xs border border-surface-border'
                        : 'text-ink-muted hover:text-ink'
                    }`}
                  >
                    <LayoutGrid className="w-3.5 h-3.5" />
                    <span>Calendar Grid</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleExportIcs}
                    className="gap-1.5 text-xs text-ink-muted hover:text-ink"
                    title="Export study schedule as .ics file for Google Calendar or Apple Calendar"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export Calendar (.ics)</span>
                  </Button>
                </div>
              </div>

              {/* RENDER VIEW: TIMELINE VS CALENDAR */}
              {planView === 'timeline' ? (
                /* Roadmap Timeline & Selected Day Tasks */
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
                                ? 'bg-indigo-50/80 border-indigo-400 text-indigo-950 font-semibold shadow-xs'
                                : 'bg-white border-surface-border text-ink-muted hover:border-zinc-300 hover:text-ink'
                            }`}
                          >
                            <div className="flex items-center gap-2.5">
                              <div
                                className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono ${
                                  dayCompleted
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : isSelected
                                    ? 'bg-indigo-600 text-white'
                                    : 'bg-surface-subtle text-ink-muted'
                                }`}
                              >
                                {day}
                              </div>
                              <span>Day {day}</span>
                              {isCurrent && (
                                <span className="text-[10px] bg-indigo-100 text-indigo-900 px-2 py-0.5 rounded-full font-mono font-semibold">
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
                        <Calendar className="w-4 h-4 text-indigo-600" />
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
                                    : 'border-zinc-300 hover:border-indigo-500 bg-white'
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
                                          className="inline-flex items-center gap-1.5 text-xs text-indigo-700 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100/70 px-2.5 py-1 rounded-md border border-indigo-200/80 transition-colors"
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
              ) : (
                /* Calendar Grid View */
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-bold text-ink">Calendar Study Schedule</h3>
                      <p className="text-xs text-ink-muted">
                        Interactive day-by-day calendar grid. Check off tasks directly or click into practice.
                      </p>
                    </div>
                    <span className="text-xs font-mono text-ink-muted">
                      {completedCount} of {totalCount} completed ({progressPercent}%)
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {days.map((day) => {
                      const dayTasks = plan.tasks.filter((t) => t.day_number === day);
                      const dayCompleted = dayTasks.length > 0 && dayTasks.every((t) => t.is_completed);
                      const isCurrent = plan.current_day === day;
                      const startDate = plan.start_date ? new Date(plan.start_date) : new Date(plan.created_at || Date.now());
                      const dayDate = new Date(startDate.getTime() + (day - 1) * 86400000);

                      return (
                        <div
                          key={day}
                          className={`rounded-2xl border p-4 flex flex-col justify-between transition-all ${
                            dayCompleted
                              ? 'bg-emerald-50/40 border-emerald-200'
                              : isCurrent
                              ? 'bg-white border-indigo-400 ring-2 ring-indigo-100 shadow-sm'
                              : 'bg-white border-surface-border hover:border-zinc-300'
                          }`}
                        >
                          <div>
                            {/* Day Header */}
                            <div className="flex items-center justify-between pb-3 border-b border-surface-border mb-3">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono font-bold ${
                                    dayCompleted
                                      ? 'bg-emerald-600 text-white'
                                      : isCurrent
                                      ? 'bg-indigo-600 text-white'
                                      : 'bg-surface-subtle text-ink'
                                  }`}
                                >
                                  {day}
                                </span>
                                <div>
                                  <h4 className="font-bold text-xs text-ink">Day {day}</h4>
                                  <span className="text-[10px] text-ink-muted">
                                    {dayDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                                  </span>
                                </div>
                              </div>

                              <div>
                                {dayCompleted ? (
                                  <Badge variant="emerald" size="sm" className="gap-1 text-[10px]">
                                    <Check className="w-3 h-3" />
                                    Done
                                  </Badge>
                                ) : isCurrent ? (
                                  <Badge variant="brand" size="sm" className="text-[10px]">
                                    Today
                                  </Badge>
                                ) : (
                                  <span className="text-[11px] font-mono text-ink-subtle">
                                    {dayTasks.filter((t) => t.is_completed).length}/{dayTasks.length}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Task List */}
                            <div className="space-y-2">
                              {dayTasks.map((task) => (
                                <div
                                  key={task.id}
                                  className={`p-2.5 rounded-xl border text-xs transition-all ${
                                    task.is_completed
                                      ? 'bg-white/60 border-surface-border text-ink-muted line-through'
                                      : 'bg-surface-subtle border-surface-border text-ink hover:bg-white'
                                  }`}
                                >
                                  <div className="flex items-start gap-2">
                                    <button
                                      type="button"
                                      onClick={() => handleToggleTask(task.id, task.is_completed)}
                                      className={`mt-0.5 w-4 h-4 rounded shrink-0 border flex items-center justify-center transition-colors ${
                                        task.is_completed
                                          ? 'bg-emerald-600 border-emerald-600 text-white'
                                          : 'border-zinc-300 hover:border-indigo-600 bg-white'
                                      }`}
                                    >
                                      {task.is_completed && <Check className="w-3 h-3" />}
                                    </button>
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-1 font-semibold text-xs leading-tight">
                                        <span className="shrink-0">{getTaskTypeIcon(task.task_type)}</span>
                                        <span className="truncate">{task.title}</span>
                                      </div>
                                      <div className="flex items-center justify-between gap-1 mt-1 text-[10px] text-ink-muted font-mono">
                                        <span>{task.estimated_minutes}m</span>
                                        <span className="uppercase">{task.task_type}</span>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="pt-3 border-t border-surface-border mt-3 flex items-center justify-between text-[11px]">
                            <span className="text-ink-muted font-mono">
                              {dayTasks.reduce((acc, t) => acc + t.estimated_minutes, 0)} mins total
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedDay(day);
                                setPlanView('timeline');
                              }}
                              className="text-indigo-600 hover:text-indigo-800 font-medium"
                            >
                              Expand &rarr;
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
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
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                    backlogFilter === f
                      ? 'bg-indigo-50 text-indigo-900 border border-indigo-300 font-semibold shadow-xs'
                      : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
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
                        variant={item.priority === 'high' ? 'brand' : 'zinc'}
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
                            ? 'brand'
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
              <span className="font-mono font-bold text-indigo-600">{customMinutes} mins/day</span>
            </div>
            <input
              type="range"
              min={15}
              max={120}
              step={15}
              value={customMinutes}
              onChange={(e) => setCustomMinutes(Number(e.target.value))}
              className="w-full accent-indigo-600"
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
                        ? 'bg-indigo-600 text-white font-semibold'
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
                <RefreshCw className={`w-3.5 h-3.5 text-indigo-600 ${loadingPreview ? 'animate-spin' : ''}`} />
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
                  <Badge variant="brand" className="gap-1 font-mono">
                    <ShieldCheck className="w-3 h-3 text-indigo-600" />
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
                          <ArrowRight className="w-3 h-3 text-indigo-600" />
                          <span className="font-bold text-indigo-700">Day {shift.new_day}</span>
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
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsAdaptModalOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
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

      {/* RESCHEDULE TO TODAY MODAL */}
      <Modal
        isOpen={isRescheduleModalOpen}
        onClose={() => setIsRescheduleModalOpen(false)}
        title="Reschedule Sprint to Today"
      >
        <div className="space-y-4">
          <p className="text-xs text-ink-muted leading-relaxed">
            Anchor your sprint to today. All your completed tasks remain preserved in your history,
            while all remaining unfinished tasks are automatically scheduled starting from today so you can
            pick up immediately without feeling behind.
          </p>

          <div className="p-3.5 bg-surface-subtle rounded-xl border border-surface-border space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-ink">
              <span className="flex items-center gap-1.5">
                <Calendar className={`w-4 h-4 text-indigo-600 ${loadingReschedulePreview ? 'animate-spin' : ''}`} />
                <span>Reschedule Preview (Anchored to Today)</span>
              </span>
              {reschedulePreview && (
                <span className="text-[11px] font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                  Today: {new Date(reschedulePreview.reschedule_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              )}
            </div>

            {reschedulePreview ? (
              <div className="space-y-3 pt-1 text-xs">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                  <div className="p-2 rounded-lg bg-emerald-50/80 border border-emerald-200 flex flex-col">
                    <span className="text-emerald-700 font-medium">Completed (Preserved)</span>
                    <span className="text-emerald-950 font-bold font-mono text-sm mt-0.5">
                      {reschedulePreview.completed_tasks_count} tasks
                    </span>
                  </div>

                  <div className="p-2 rounded-lg bg-indigo-50/80 border border-indigo-200 flex flex-col">
                    <span className="text-indigo-700 font-medium">Remaining (Rescheduled)</span>
                    <span className="text-indigo-950 font-bold font-mono text-sm mt-0.5">
                      {reschedulePreview.remaining_tasks_count} tasks
                    </span>
                  </div>

                  <div className="p-2 rounded-lg bg-white border border-surface-border flex flex-col col-span-2 sm:col-span-1">
                    <span className="text-ink-subtle font-medium">New Target Finish</span>
                    <span className="text-ink font-bold font-mono text-xs mt-0.5 truncate">
                      {new Date(reschedulePreview.new_target_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-ink-subtle uppercase tracking-wider">
                    Upcoming Sequence
                  </div>
                  {reschedulePreview.shifted_tasks.length > 0 ? (
                    <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1">
                      {reschedulePreview.shifted_tasks.map((shift) => (
                        <div
                          key={shift.task_id}
                          className={`p-2.5 rounded-lg border text-xs flex items-center justify-between gap-3 ${
                            shift.is_today
                              ? 'bg-indigo-50/70 border-indigo-300 ring-1 ring-indigo-400/30'
                              : 'bg-white border-surface-border'
                          }`}
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              {shift.is_today && (
                                <Badge variant="brand" size="sm" className="px-1.5 py-0 text-[10px]">
                                  TODAY
                                </Badge>
                              )}
                              <span className="font-semibold text-ink truncate">
                                {shift.title}
                              </span>
                            </div>
                            <span className="text-[11px] text-ink-muted">
                              {new Date(shift.new_date).toLocaleDateString(undefined, {
                                weekday: 'short',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 font-mono text-[11px]">
                            <span className="text-ink-subtle">Day {shift.old_day}</span>
                            <ArrowRight className="w-3 h-3 text-indigo-600" />
                            <span className="font-bold text-indigo-700">Day {shift.new_day}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-ink-subtle italic py-2">
                      All tasks on your current roadmap have already been finished!
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink-subtle py-2">Calculating preview schedule...</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-surface-border">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsRescheduleModalOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handleRescheduleToToday}
              isLoading={actionLoading}
              disabled={!reschedulePreview || reschedulePreview.shifted_tasks.length === 0}
            >
              Confirm & Reschedule from Today
            </Button>
          </div>
        </div>
      </Modal>

      {/* EVALUATION SPRINT CONFIGURATION MODAL */}
      <Modal
        isOpen={isEvalConfigOpen}
        onClose={() => setIsEvalConfigOpen(false)}
        title="Generate Targeted Study Sprint"
      >
        <form onSubmit={handleGenerateFromEvaluation} className="space-y-4 text-xs">
          <p className="text-ink-muted leading-relaxed">
            Configure the pace and daily commitment for your personalized curriculum synthesized from your recent
            interview evaluation diagnostics.
          </p>

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Sprint Duration (Days)
            </label>
            <div className="grid grid-cols-4 gap-2 mb-2">
              {[7, 14, 21, 30].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setPrepDays(d)}
                  className={`py-2 px-3 rounded-lg border font-mono font-semibold transition-all ${
                    prepDays === d
                      ? 'bg-indigo-50 border-indigo-500 text-indigo-900 shadow-xs'
                      : 'bg-white border-surface-border text-ink-muted hover:border-zinc-300'
                  }`}
                >
                  {d} Days
                </button>
              ))}
            </div>
            <Input
              type="number"
              min={3}
              max={60}
              value={prepDays}
              onChange={(e) => setPrepDays(Math.max(3, Math.min(60, Number(e.target.value))))}
              helperText="Choose between a 3-day sprint and a 60-day deep roadmap."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Daily Study Commitment (Minutes)
            </label>
            <div className="grid grid-cols-5 gap-1.5 mb-2">
              {[30, 45, 60, 90, 120].map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setPrepMinutes(m)}
                  className={`py-1.5 px-2 rounded-lg border font-mono font-semibold text-[11px] transition-all ${
                    prepMinutes === m
                      ? 'bg-indigo-50 border-indigo-500 text-indigo-900 shadow-xs'
                      : 'bg-white border-surface-border text-ink-muted hover:border-zinc-300'
                  }`}
                >
                  {m}m
                </button>
              ))}
            </div>
            <Input
              type="number"
              min={15}
              max={180}
              step={15}
              value={prepMinutes}
              onChange={(e) => setPrepMinutes(Math.max(15, Math.min(180, Number(e.target.value))))}
              helperText="How many minutes per day can you commit?"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Target Interview Date (Optional)
            </label>
            <input
              type="date"
              value={prepTargetDate}
              onChange={(e) => setPrepTargetDate(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <p className="text-[11px] text-ink-muted mt-1">
              If provided, Planly will pace the sprint backward from your target interview date.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-surface-border">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsEvalConfigOpen(false)}
              disabled={isGeneratingFromEval}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isGeneratingFromEval}
            >
              Generate Calibrated Sprint
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

