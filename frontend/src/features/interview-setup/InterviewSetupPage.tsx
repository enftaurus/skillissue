import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import { Interview, JobDescription, Resume, CodeforcesProblem } from '../../lib/types';
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

const DSA_TOPICS = [
  'Dynamic Programming',
  'Binary Search',
  'Trees & Graphs',
  'Greedy Algorithms',
  'Two Pointers',
  'Data Structures',
  'Math & Number Theory',
  'Strings',
  'Arrays',
  'Bit Manipulation',
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

  // Codeforces Adaptive Recommendation State
  const [selectedCfProblemId, setSelectedCfProblemId] = useState<string>('');
  const [cfRecommendations, setCfRecommendations] = useState<CodeforcesProblem[]>([]);
  const [isLoadingCfRecs, setIsLoadingCfRecs] = useState<boolean>(false);

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

  useEffect(() => {
    if (category === 'dsa') {
      const fetchCfRecs = async () => {
        setIsLoadingCfRecs(true);
        try {
          const skillsParam = selectedSkills.join(',');
          const data = await api.get<CodeforcesProblem[]>(
            `/coding/codeforces/recommended?difficulty=${difficulty}&skills=${encodeURIComponent(skillsParam)}&limit=5`
          );
          setCfRecommendations(data || []);
        } catch (e) {
          console.warn('Failed to fetch Codeforces recommendations', e);
        } finally {
          setIsLoadingCfRecs(false);
        }
      };
      fetchCfRecs();
    }
  }, [category, difficulty, selectedSkills]);

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
          coding_problem_id: category === 'dsa' && selectedCfProblemId ? selectedCfProblemId : undefined,
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
          coding_problem_id: category === 'dsa' && selectedCfProblemId ? selectedCfProblemId : undefined,
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
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
          <Compass className="w-7 h-7 text-indigo-600" />
          Setup Practice Interview
        </h1>
        <p className="mt-2 text-sm sm:text-base text-slate-500 leading-relaxed">
          Choose between customized skill-domain practice or targeted Job Description preparation.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Mode Switcher */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label
          onClick={() => setMode('domain')}
          className={`p-6 rounded-2xl border cursor-pointer transition-all ${
            mode === 'domain'
              ? 'border-indigo-600 bg-indigo-50/40 ring-2 ring-indigo-500/20 shadow-xs'
              : 'border-slate-200/80 hover:bg-slate-50 bg-white'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-base text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              Domain-Based Practice
            </span>
            <input
              type="radio"
              checked={mode === 'domain'}
              onChange={() => setMode('domain')}
              className="accent-indigo-600 w-4 h-4"
            />
          </div>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
            Practice chosen skills (e.g. Concurrency, SQL, Docker). Upload an optional resume to auto-detect and preselect your stack.
          </p>
        </label>

        <label
          onClick={() => setMode('jd')}
          className={`p-6 rounded-2xl border cursor-pointer transition-all ${
            mode === 'jd'
              ? 'border-indigo-600 bg-indigo-50/40 ring-2 ring-indigo-500/20 shadow-xs'
              : 'border-slate-200/80 hover:bg-slate-50 bg-white'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-base text-slate-900 flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-indigo-600" />
              Job Description (JD) Mode
            </span>
            <input
              type="radio"
              checked={mode === 'jd'}
              onChange={() => setMode('jd')}
              className="accent-indigo-600 w-4 h-4"
            />
          </div>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
            Paste an actual job posting. We extract required skills and interview expectations automatically without manual re-entry.
          </p>
        </label>
      </div>

      {/* Category Selection */}
      <Card className="p-6 sm:p-7 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Interview Category
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
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
                onClick={() => {
                  setCategory(cat.id as any);
                  if (cat.id === 'dsa' && selectedSkills.includes('FastAPI')) {
                    setSelectedSkills(['Dynamic Programming', 'Binary Search', 'Trees & Graphs']);
                  }
                }}
                className={`p-4 rounded-xl border text-left transition-all ${
                  isSel
                    ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-500/20 shadow-xs'
                    : 'border-slate-200/80 hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-5 h-5 mb-2.5 ${isSel ? 'text-indigo-600' : 'text-slate-400'}`} />
                <div className="font-semibold text-sm text-slate-900">{cat.label}</div>
                <div className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">{cat.desc}</div>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Mode-Specific Configuration */}
      {mode === 'domain' ? (
        <Card className="p-6 sm:p-7 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">
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
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-indigo-600" />
                Upload Resume (Optional)
              </label>
              {uploadedResume && (
                <span className="text-xs text-indigo-600 font-semibold flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" />
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
              Select {category === 'dsa' ? 'Algorithmic Topics' : 'Skills'} to Practice ({selectedSkills.length} selected)
            </label>
            <div className="flex flex-wrap gap-2">
              {(category === 'dsa' ? DSA_TOPICS : COMMON_SKILLS).map((skill) => {
                const isSelected = selectedSkills.includes(skill);
                return (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => toggleSkill(skill)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      isSelected
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm font-semibold'
                        : 'bg-white text-slate-700 border-slate-200/80 hover:bg-slate-50'
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
        <Card className="p-6 sm:p-7 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">
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
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Paste Job Description Text
            </label>
            <textarea
              rows={6}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste full job description text here..."
              className="w-full p-3.5 text-sm bg-white border border-slate-200/80 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 font-sans"
            />
          </div>

          {!extractedJd ? (
            <Button
              type="button"
              variant="secondary"
              onClick={handleExtractJd}
              isLoading={isExtractingJd}
            >
              <Sparkles className="w-4 h-4 mr-1.5 text-indigo-600" />
              Extract Role Requirements
            </Button>
          ) : (
            <div className="p-5 bg-indigo-50/40 rounded-2xl border border-indigo-200/80 space-y-3.5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-indigo-950 uppercase tracking-wider">
                  Extracted Requirements Summary
                </span>
                <Badge variant="indigo">Verified from JD</Badge>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {extractedJd.extracted_skills.map((s) => (
                  <Badge key={s} variant="zinc" size="sm" className="text-xs">
                    {s}
                  </Badge>
                ))}
              </div>
              {extractedJd.extracted_requirements.length > 0 && (
                <ul className="list-disc list-inside text-xs sm:text-sm text-slate-600 space-y-1">
                  {extractedJd.extracted_requirements.slice(0, 3).map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Codeforces Adaptive Problem Matcher for DSA Interviews */}
      {category === 'dsa' && (
        <Card className="p-6 sm:p-7 rounded-2xl border border-indigo-200/80 bg-gradient-to-br from-indigo-50/40 via-white to-white shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 animate-pulse" />
              <label className="text-xs font-bold text-indigo-950 uppercase tracking-wider">
                Codeforces Adaptive Problem Matcher
              </label>
            </div>
            <span className="text-[11px] font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200/60 font-semibold">
              Difficulty Rating: {difficulty === 'junior' ? '800 - 1200' : difficulty === 'intermediate' ? '1200 - 1700' : '1700 - 2400'}
            </span>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            The interviewer will present an algorithmic challenge from Codeforces calibrated to your selected difficulty and topic focus.
          </p>

          <div className="space-y-2 pt-1">
            {/* Option 0: Dynamic Auto-Match */}
            <label
              onClick={() => setSelectedCfProblemId('')}
              className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                selectedCfProblemId === ''
                  ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20 shadow-xs'
                  : 'border-slate-200 hover:bg-slate-50 bg-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <input
                  type="radio"
                  name="cf_problem"
                  checked={selectedCfProblemId === ''}
                  onChange={() => setSelectedCfProblemId('')}
                  className="accent-indigo-600 w-4 h-4"
                />
                <div>
                  <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    <span>🎯 Dynamic Adaptive Selection</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold">
                      Recommended
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    Let the AI interviewer automatically assign the best Codeforces challenge based on your topics and real-time level
                  </div>
                </div>
              </div>
            </label>

            {/* Recommended Problems */}
            {isLoadingCfRecs ? (
              <div className="p-4 text-center text-xs text-indigo-600 flex items-center justify-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                <span>Fetching tailored Codeforces challenges...</span>
              </div>
            ) : (
              cfRecommendations.map((p) => {
                const isSelected = selectedCfProblemId === p.id;
                return (
                  <label
                    key={p.id}
                    onClick={() => setSelectedCfProblemId(p.id)}
                    className={`p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20 shadow-xs'
                        : 'border-slate-200 hover:bg-slate-50 bg-white'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="cf_problem"
                        checked={isSelected}
                        onChange={() => setSelectedCfProblemId(p.id)}
                        className="accent-indigo-600 w-4 h-4"
                      />
                      <div>
                        <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                          <span>{p.title}</span>
                          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            Rating: {p.rating}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                          <span>Tags: {p.tags?.slice(0, 3).join(', ')}</span>
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-indigo-600 hover:underline inline-flex items-center gap-0.5"
                          >
                            View on CF ↗
                          </a>
                        </div>
                      </div>
                    </div>
                  </label>
                );
              })
            )}
          </div>
        </Card>
      )}

      {/* Parameters: Difficulty & Duration */}
      <Card className="p-6 sm:p-7 rounded-2xl border border-slate-200/80 shadow-xs grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
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
                className={`py-2.5 px-2 text-xs font-medium rounded-xl border text-center transition-all ${
                  difficulty === d.id
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm font-semibold'
                    : 'bg-white text-slate-700 border-slate-200/80 hover:bg-slate-50'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
            Target Duration: {duration} Minutes
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[15, 20, 30].map((mins) => (
              <button
                key={mins}
                type="button"
                onClick={() => setDuration(mins)}
                className={`py-2.5 px-2 text-xs font-medium rounded-xl border text-center transition-all ${
                  duration === mins
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm font-semibold'
                    : 'bg-white text-slate-700 border-slate-200/80 hover:bg-slate-50'
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
