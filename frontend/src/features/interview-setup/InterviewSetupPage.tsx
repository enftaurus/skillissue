import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import { Interview, JobDescription, Resume } from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import {
  Briefcase,
  Code2,
  Compass,
  FileText,
  Layers,
  Sparkles,
  Upload,
  UserCheck,
  Zap,
} from 'lucide-react';

const COMMON_SKILLS = [
  'Python',
  'FastAPI',
  'PostgreSQL',
  'Docker',
  'Redis',
  'System Design',
  'Async Concurrency',
  'Distributed Systems',
  'Kafka',
  'C++',
  'Java',
  'Linux Internals',
  'REST APIs',
  'SQL Optimization',
  'Microservices',
];

export const InterviewSetupPage: React.FC = () => {
  const navigate = useNavigate();

  // Mode: 'domain' or 'jd'
  const [mode, setMode] = useState<'domain' | 'jd'>('domain');
  const [category, setCategory] = useState<'technical' | 'behavioral' | 'dsa' | 'managerial'>('technical');
  const [difficulty, setDifficulty] = useState<'junior' | 'intermediate' | 'advanced'>('intermediate');
  const [targetRole, setTargetRole] = useState('Software Engineer');
  const [duration, setDuration] = useState(20);

  // Domain Mode State
  const [selectedSkills, setSelectedSkills] = useState<string[]>(['Python', 'FastAPI', 'PostgreSQL']);
  const [customSkill, setCustomSkill] = useState('');
  const [uploadedResume, setUploadedResume] = useState<Resume | null>(null);
  const [isUploadingResume, setIsUploadingResume] = useState(false);

  // JD Mode State
  const [jdTitle, setJdTitle] = useState('Backend Software Engineer');
  const [jdCompany, setJdCompany] = useState('');
  const [jdText, setJdText] = useState('');
  const [extractedJd, setExtractedJd] = useState<JobDescription | null>(null);
  const [isExtractingJd, setIsExtractingJd] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
  };

  const addCustomSkill = (e: React.FormEvent) => {
    e.preventDefault();
    if (customSkill.trim() && !selectedSkills.includes(customSkill.trim())) {
      setSelectedSkills((prev) => [...prev, customSkill.trim()]);
      setCustomSkill('');
    }
  };

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingResume(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post<Resume>('/resumes/upload', formData);
      setUploadedResume(res);
      // Preselect detected skills in domain mode
      if (res.extracted_skills && res.extracted_skills.length > 0) {
        setSelectedSkills((prev) => Array.from(new Set([...prev, ...res.extracted_skills])));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to parse resume.');
    } finally {
      setIsUploadingResume(false);
    }
  };

  const handleExtractJd = async () => {
    if (!jdText.trim() || jdText.length < 30) {
      setError('Please paste a substantial job description (at least 30 characters).');
      return;
    }

    setIsExtractingJd(true);
    setError('');

    try {
      const res = await api.post<JobDescription>('/job-descriptions', {
        title: jdTitle,
        company: jdCompany,
        raw_text: jdText,
      });
      setExtractedJd(res);
    } catch (err: any) {
      setError(err.message || 'Failed to extract requirements from JD.');
    } finally {
      setIsExtractingJd(false);
    }
  };

  const handleStartInterview = async () => {
    setError('');
    setIsLoading(true);

    try {
      let interview: Interview;

      if (mode === 'domain') {
        if (selectedSkills.length === 0) {
          setError('Please select at least one skill to practice.');
          setIsLoading(false);
          return;
        }

        interview = await api.post<Interview>('/interviews/domain', {
          category,
          domain_skills: selectedSkills,
          target_role: targetRole,
          difficulty,
          resume_id: uploadedResume?.id,
          target_duration_minutes: duration,
        });
      } else {
        // JD Mode
        if (!extractedJd) {
          setError('Please extract requirements from the job description first.');
          setIsLoading(false);
          return;
        }

        interview = await api.post<Interview>('/interviews/jd', {
          category,
          jd_id: extractedJd.id,
          difficulty,
          resume_id: uploadedResume?.id,
          target_duration_minutes: duration,
        });
      }

      navigate(`/interviews/${interview.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to initiate interview session.');
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
          <Compass className="w-6 h-6 text-lime-700" />
          Setup Practice Interview
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Choose between customized skill-domain practice or targeted Job Description preparation.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-900 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Mode Switcher */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label
          onClick={() => setMode('domain')}
          className={`p-5 rounded-xl border cursor-pointer transition-all ${
            mode === 'domain'
              ? 'border-lime-600 bg-lime-50/50 ring-2 ring-lime-600 shadow-sm'
              : 'border-surface-border hover:bg-surface-subtle bg-white'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-base text-ink flex items-center gap-2">
              <Layers className="w-4 h-4 text-lime-700" />
              Domain-Based Practice
            </span>
            <input
              type="radio"
              checked={mode === 'domain'}
              onChange={() => setMode('domain')}
              className="accent-lime-600"
            />
          </div>
          <p className="text-xs text-ink-muted leading-relaxed">
            Practice chosen skills (e.g. Concurrency, SQL, Docker). Upload an optional resume to auto-detect and preselect your stack.
          </p>
        </label>

        <label
          onClick={() => setMode('jd')}
          className={`p-5 rounded-xl border cursor-pointer transition-all ${
            mode === 'jd'
              ? 'border-lime-600 bg-lime-50/50 ring-2 ring-lime-600 shadow-sm'
              : 'border-surface-border hover:bg-surface-subtle bg-white'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-base text-ink flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-lime-700" />
              Job Description (JD) Mode
            </span>
            <input
              type="radio"
              checked={mode === 'jd'}
              onChange={() => setMode('jd')}
              className="accent-lime-600"
            />
          </div>
          <p className="text-xs text-ink-muted leading-relaxed">
            Paste an actual job posting. We extract required skills and interview expectations automatically without manual re-entry.
          </p>
        </label>
      </div>

      {/* Category Selection */}
      <Card className="space-y-4">
        <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider">
          Interview Category
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { id: 'technical', label: 'Technical Depth', desc: 'Architecture, systems, edge cases', icon: Zap },
            { id: 'dsa', label: 'DSA & Coding', desc: 'Algorithms, complexity & sandbox editor', icon: Code2 },
            { id: 'behavioral', label: 'HR / Behavioral', desc: 'STAR format, ownership, impact', icon: UserCheck },
            { id: 'managerial', label: 'Managerial & Lead', desc: 'Trade-offs, tech debt vs velocity', icon: Briefcase },
          ].map((cat) => {
            const Icon = cat.icon;
            const isSel = category === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategory(cat.id as any)}
                className={`p-3.5 rounded-lg border text-left transition-all ${
                  isSel
                    ? 'border-lime-600 bg-lime-50/60 ring-1 ring-lime-600'
                    : 'border-surface-border hover:bg-surface-subtle'
                }`}
              >
                <Icon className={`w-4 h-4 mb-2 ${isSel ? 'text-lime-700' : 'text-ink-subtle'}`} />
                <div className="font-semibold text-xs text-ink">{cat.label}</div>
                <div className="text-[11px] text-ink-subtle mt-0.5 line-clamp-2">{cat.desc}</div>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Mode-Specific Configuration */}
      {mode === 'domain' ? (
        <Card className="space-y-6">
          {/* Target Role */}
          <Input
            label="Target Engineering Role"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="e.g. Backend Software Engineer, Distributed Systems Engineer"
          />

          {/* Optional Resume Upload */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-lime-700" />
                Upload Resume (Optional)
              </label>
              {uploadedResume && (
                <span className="text-xs text-lime-700 font-medium flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  {uploadedResume.extracted_skills.length} skills extracted
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              <label className="cursor-pointer inline-flex items-center gap-2 px-3 py-2 border border-surface-border rounded-md text-xs font-medium text-ink bg-surface-subtle hover:bg-surface-muted transition-colors">
                <Upload className="w-3.5 h-3.5 text-ink-muted" />
                {isUploadingResume ? 'Analyzing Resume...' : 'Choose PDF or Text File'}
                <input
                  type="file"
                  accept=".pdf,.txt,.md"
                  onChange={handleResumeUpload}
                  disabled={isUploadingResume}
                  className="hidden"
                />
              </label>
              {uploadedResume && (
                <span className="text-xs text-ink-muted font-mono">{uploadedResume.file_name}</span>
              )}
            </div>
          </div>

          {/* Skill Selector */}
          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
              Select Skills to Practice ({selectedSkills.length} selected)
            </label>
            <div className="flex flex-wrap gap-2">
              {COMMON_SKILLS.map((skill) => {
                const isSelected = selectedSkills.includes(skill);
                return (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => toggleSkill(skill)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      isSelected
                        ? 'bg-lime-600 text-white border-lime-600 shadow-sm'
                        : 'bg-white text-ink border-surface-border hover:bg-surface-subtle'
                    }`}
                  >
                    {skill}
                  </button>
                );
              })}
            </div>

            {/* Custom Skill Input */}
            <form onSubmit={addCustomSkill} className="mt-4 flex gap-2">
              <Input
                placeholder="Add custom skill or framework..."
                value={customSkill}
                onChange={(e) => setCustomSkill(e.target.value)}
                className="max-w-xs"
              />
              <Button type="submit" variant="secondary" size="md">
                Add
              </Button>
            </form>
          </div>
        </Card>
      ) : (
        /* JD Mode Form */
        <Card className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Role Title"
              value={jdTitle}
              onChange={(e) => setJdTitle(e.target.value)}
              placeholder="e.g. Senior Backend Engineer"
            />
            <Input
              label="Company Name (Optional)"
              value={jdCompany}
              onChange={(e) => setJdCompany(e.target.value)}
              placeholder="e.g. Stripe, Netflix, Startup"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Paste Job Description Text
            </label>
            <textarea
              rows={6}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste full job description text here..."
              className="w-full px-3 py-2 text-sm bg-white border border-surface-border rounded-md text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-lime-500 font-sans"
            />
          </div>

          {!extractedJd ? (
            <Button
              type="button"
              variant="secondary"
              onClick={handleExtractJd}
              isLoading={isExtractingJd}
            >
              <Sparkles className="w-3.5 h-3.5 mr-1 text-lime-700" />
              Extract Role Requirements
            </Button>
          ) : (
            <div className="p-4 bg-surface-warm rounded-lg border border-lime-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-lime-900 uppercase tracking-wider">
                  Extracted Requirements Summary
                </span>
                <Badge variant="lime">Verified from JD</Badge>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {extractedJd.extracted_skills.map((s) => (
                  <Badge key={s} variant="zinc" size="sm">
                    {s}
                  </Badge>
                ))}
              </div>
              {extractedJd.extracted_requirements.length > 0 && (
                <ul className="list-disc list-inside text-xs text-ink-muted space-y-1">
                  {extractedJd.extracted_requirements.slice(0, 3).map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Parameters: Difficulty & Duration */}
      <Card className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div>
          <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
            Target Difficulty Level
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'junior', label: 'Junior / Intern' },
              { id: 'intermediate', label: 'Mid-Level' },
              { id: 'advanced', label: 'Senior / Staff' },
            ].map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => setDifficulty(d.id as any)}
                className={`py-2 px-2 text-xs font-medium rounded-md border text-center transition-colors ${
                  difficulty === d.id
                    ? 'bg-lime-600 text-white border-lime-600'
                    : 'bg-white text-ink border-surface-border hover:bg-surface-subtle'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
            Target Duration: {duration} Minutes
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[15, 20, 30].map((mins) => (
              <button
                key={mins}
                type="button"
                onClick={() => setDuration(mins)}
                className={`py-2 px-2 text-xs font-medium rounded-md border text-center transition-colors ${
                  duration === mins
                    ? 'bg-lime-600 text-white border-lime-600'
                    : 'bg-white text-ink border-surface-border hover:bg-surface-subtle'
                }`}
              >
                {mins} Mins
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Start Button */}
      <div className="flex justify-end pt-4">
        <Button
          size="lg"
          variant="primary"
          onClick={handleStartInterview}
          isLoading={isLoading}
          className="w-full sm:w-auto"
        >
          Start Practice Interview Session
        </Button>
      </div>
    </div>
  );
};
