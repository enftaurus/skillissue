import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import {
  Boxes,
  ShieldAlert,
  Layers,
  Clock,
  Sparkles,
  ArrowRight,
  Terminal,
  FileCode,
  Lock,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

interface ProjectSummary {
  id: string;
  title: string;
  slug: string;
  difficulty: 'junior' | 'mid' | 'senior' | 'staff';
  estimated_minutes: number;
  description: string;
  tags: string[];
  icon: string;
  domain: string;
}

export const ProjectCatalogPage: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    api.get<ProjectSummary[]>('/projects')
      .then((data) => {
        setProjects(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load projects:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 sm:p-8 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                Work Simulation
              </span>
              <span className="text-xs text-slate-400 font-mono">• 25-Min Time Limit</span>
              <span className="text-xs text-slate-400 font-mono">• Read-Only AI Bot</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              AI-Assisted Coding Projects
            </h1>
            <p className="text-sm text-slate-600 max-w-2xl leading-relaxed">
              Tier-1 engineering take-home challenges on a real multi-file codebase. Collaborate with an in-browser{' '}
              <strong>Read-Only AI Pair Programmer</strong>, verify changes against automated CI/CD test suites, and receive{' '}
              <strong>Prompt Quality AI Feedback</strong> on how to communicate like a senior engineer.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-900">2 Demo Projects Available</div>
              <div className="text-[11px] text-slate-500">FastAPI, Redis, Async Tasks</div>
            </div>
            <div className="w-12 h-12 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-100">
              <Boxes className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Feature Highlights Pills */}
        <div className="pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700">
            <Lock className="w-4 h-4 text-indigo-600 shrink-0" />
            <span>
              <strong>Read-Only AI Copilot:</strong> Explains logic; zero write permission.
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-700">
            <Terminal className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Sandboxed CI/CD Runner:</strong> Real Pytest verification inside Bubblewrap.
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-700">
            <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Prompt Quality Evaluator:</strong> Flags amateur prompts with senior rewrites.
            </span>
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
          <span className="text-xs text-slate-500">Loading project environments...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}`)}
              className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group cursor-pointer"
            >
              <div className="space-y-4">
                {/* Card Top: Badges & Icon */}
                <div className="flex items-start justify-between gap-3">
                  <div className="w-11 h-11 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-center text-indigo-600 group-hover:scale-105 transition-transform">
                    {project.id === 'distributed-rate-limiter' ? (
                      <ShieldAlert className="w-6 h-6 text-indigo-600" />
                    ) : (
                      <Layers className="w-6 h-6 text-indigo-600" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        project.difficulty === 'senior'
                          ? 'rose'
                          : project.difficulty === 'mid'
                          ? 'amber'
                          : 'emerald'
                      }
                      size="sm"
                      className="capitalize font-mono text-[10px]"
                    >
                      {project.difficulty}
                    </Badge>
                    <span className="flex items-center gap-1 text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200/60">
                      <Clock className="w-3 h-3" />
                      <span>{project.estimated_minutes} min</span>
                    </span>
                  </div>
                </div>

                {/* Card Title & Domain */}
                <div>
                  <span className="text-[11px] font-semibold text-indigo-600 uppercase tracking-wide">
                    {project.domain}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors mt-0.5">
                    {project.title}
                  </h3>
                </div>

                {/* Description */}
                <p className="text-xs text-slate-600 leading-relaxed">{project.description}</p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {project.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] font-medium text-slate-600 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-200/60"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Card Footer: Action Button */}
              <div className="pt-6 mt-6 border-t border-slate-100 flex items-center justify-between">
                <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                  <FileCode className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    {project.id === 'distributed-rate-limiter' ? 'src/limiter.py' : 'src/dispatcher.py'} (Editable)
                  </span>
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => navigate(`/projects/${project.id}`)}
                  className="gap-1.5 text-xs font-semibold shadow-sm"
                >
                  <span>Launch Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
