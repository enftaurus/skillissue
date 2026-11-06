import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Brain,
  Bug,
  CheckCircle2,
  ChevronRight,
  Code2,
  LineChart,
  Mic,
  Quote,
  Radio,
  ShieldCheck,
  Sparkles,
  Target,
  Wand2,
} from 'lucide-react';

/* ----------------------------------------------------------------------------- hooks */

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return;
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.01, rootMargin: '0px 0px -8% 0px' }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return { ref, className: visible ? 'animate-fade-up' : 'opacity-0' };
}

function useTypewriter(lines: string[], speed = 28, pause = 1800) {
  const [lineIdx, setLineIdx] = useState(0);
  const [text, setText] = useState('');
  useEffect(() => {
    const full = lines[lineIdx];
    if (text.length < full.length) {
      const t = setTimeout(() => setText(full.slice(0, text.length + 1)), speed);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => {
      setText('');
      setLineIdx((i) => (i + 1) % lines.length);
    }, pause);
    return () => clearTimeout(t);
  }, [text, lineIdx, lines, speed, pause]);
  return { text, lineIdx };
}

const Reveal: React.FC<{ children: React.ReactNode; className?: string; delay?: number }> = ({ children, className = '', delay = 0 }) => {
  const r = useReveal<HTMLDivElement>();
  return (
    <div ref={r.ref} className={`${r.className} ${className}`} style={{ animationDelay: `${delay}ms` }}>
      {children}
    </div>
  );
};

/* ----------------------------------------------------------------------------- hero demo */

const INTERVIEW_LINES = [
  'You said Redis made it 10x faster. How did you measure that?',
  'Let me stop you there. What did you personally build?',
  'Say an endpoint suddenly takes 3 seconds. Where do you look first?',
];
const CANDIDATE_LINES = ['Um, we just saw it was faster…', 'So in college we had this fest and…', "I'd check the slow query log, then p95 by route."];

const HeroDemo: React.FC = () => {
  const { text, lineIdx } = useTypewriter(INTERVIEW_LINES);
  return (
    <div className="relative">
      <div className="absolute -inset-6 bg-gradient-to-tr from-brand-200/50 via-white to-emerald-100/50 blur-2xl rounded-[2rem]" aria-hidden />
      <div className="relative rounded-2xl border border-slate-200 bg-white shadow-elevated overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-rose-400 animate-pulse-ring" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
            </span>
            Live interview · Technical
          </div>
          <span className="font-mono text-[11px] text-slate-400">Answer 3 of 8</span>
        </div>
        <div className="p-5 space-y-4 min-h-[260px]">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white grid place-items-center text-xs font-bold shrink-0">P</div>
            <div className="rounded-2xl rounded-tl-sm bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-900 max-w-[85%]">
              <span className="block text-[11px] text-slate-500 mb-0.5">Priya · Staff Engineer</span>
              {text}
              <span className="inline-block w-[2px] h-4 bg-slate-900 align-middle ml-0.5 animate-blink" />
            </div>
          </div>
          <div className="flex items-start gap-3 justify-end">
            <div className="rounded-2xl rounded-tr-sm bg-brand-600 text-white px-4 py-3 text-sm max-w-[80%]">
              <div className="flex items-end gap-[3px] h-5 mb-1.5" aria-hidden>
                {Array.from({ length: 22 }).map((_, i) => (
                  <span key={i} className="w-[3px] h-full bg-white/80 rounded-full origin-bottom animate-wave" style={{ animationDelay: `${(i * 73) % 900}ms` }} />
                ))}
              </div>
              <span className="text-white/90">{CANDIDATE_LINES[(lineIdx + 2) % CANDIDATE_LINES.length]}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {['Probing a claim', 'No praise', 'Your words, quoted'].map((c) => (
              <span key={c} className="text-[11px] px-2 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">{c}</span>
            ))}
          </div>
        </div>
      </div>
      <div className="hidden sm:block absolute -bottom-16 -left-10 w-64 rounded-xl border border-slate-200 bg-white shadow-elevated p-4 animate-float">
        <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">Self-awareness</div>
        <div className="mt-1 text-sm text-slate-900">You rated system design <b>5/5</b>. Evidence says <b>2/5</b>.</div>
        <div className="mt-2 h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full w-2/5 bg-gradient-to-r from-amber-400 to-rose-500" />
        </div>
      </div>
      <div className="hidden sm:block absolute -top-6 -right-6 rounded-xl border border-slate-200 bg-white shadow-elevated px-3 py-2 animate-float" style={{ animationDelay: '1.5s' }}>
        <div className="flex items-center gap-2 text-xs text-slate-700">
          <Radio className="w-4 h-4 text-brand-600" /> Real voice, real interruptions
        </div>
      </div>
    </div>
  );
};

/* ----------------------------------------------------------------------------- code reading demo */

const CODE = [
  'def get(self, key, default=None):',
  '    if key not in self._data:',
  '        return default',
  '    value, expires_at = self._data[key]',
  '    self._data.move_to_end(key)',
  '    if self.clock() >= expires_at:',
  '        return default',
  '    return value',
];

const CodeReadingDemo: React.FC = () => {
  const [picked, setPicked] = useState<number | null>(null);
  const correct = picked === 4;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-card overflow-hidden">
      <div className="px-4 py-2.5 border-b border-slate-100 flex items-center justify-between">
        <span className="font-mono text-xs text-slate-600">cache.py</span>
        <span className="text-[11px] text-slate-400">Click the line that evicts live entries</span>
      </div>
      <pre className="font-mono text-[12px] sm:text-[13px] leading-7 [font-variant-ligatures:none] py-2 overflow-x-auto">
        {CODE.map((l, i) => (
          <button
            key={i}
            onClick={() => setPicked(i)}
            className={`w-full text-left flex transition-colors ${
              picked === i ? (correct ? 'bg-emerald-50' : 'bg-rose-50') : 'hover:bg-brand-50/60'
            }`}
          >
            <span className="w-10 text-right pr-3 text-slate-400 select-none">{i + 12}</span>
            <code className="text-slate-800 whitespace-pre">{l}</code>
          </button>
        ))}
      </pre>
      <div className="px-4 py-3 border-t border-slate-100 text-sm min-h-[56px]" aria-live="polite">
        {picked === null && <span className="text-slate-500">Your move. Real rounds grade the line and the reason.</span>}
        {picked !== null && correct && (
          <span className="text-emerald-800 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            L16. An expired key gets refreshed to most-recent before the expiry check and is never deleted, so a live key is evicted instead.
          </span>
        )}
        {picked !== null && !correct && (
          <span className="text-rose-800">Not that one. Reviewer: “What does get() do with a key whose time has passed?”</span>
        )}
      </div>
    </div>
  );
};

/* ----------------------------------------------------------------------------- page */

const ROUNDS = ['Technical deep dives', 'DSA with a live editor', 'Behavioral (STAR)', 'Managerial trade-offs', 'Code reading', 'AI-assisted projects', 'Live voice calls', 'Company tracks'];

const USPS = [
  {
    icon: Mic,
    title: 'Interviews that feel real',
    body: 'A named interviewer with an agenda, follow-ups on what you actually said, interruptions when you ramble, and time for your questions at the end. Talk out loud over a live voice call.',
  },
  {
    icon: Brain,
    title: 'Code comprehension, big-tech level',
    body: 'Read infrastructure code you didn’t write: trace exact output, find the line that breaks in production, write the review comment. Graded against a hidden key, not vibes.',
  },
  {
    icon: Wand2,
    title: 'AI-assisted coding, graded properly',
    body: 'Work with an AI pair programmer that won’t write the solution. We score how well you direct it from a server-side log, separately from whether your tests pass.',
  },
  {
    icon: ShieldCheck,
    title: 'Evidence, not encouragement',
    body: 'Every finding quotes your transcript. Your self-rating is put next to the evidence, so you can see exactly where you overrate yourself.',
  },
];

const LOOP = [
  { icon: Target, label: 'Practice', sub: 'Real rounds, real pressure' },
  { icon: CheckCircle2, label: 'Self-evaluate', sub: 'Rate yourself first' },
  { icon: Quote, label: 'Evidence', sub: 'Findings quote your words' },
  { icon: Sparkles, label: 'Improve', sub: 'A plan for your gaps' },
  { icon: LineChart, label: 'Reassess', sub: 'Prove you got better' },
];

export const LandingPage: React.FC = () => {
  return (
    <div className="bg-white text-slate-900 overflow-x-hidden">
      {/* nav */}
      <header className="sticky top-0 z-30 backdrop-blur bg-white/80 border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2 font-bold">
            <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white grid place-items-center">
              <Sparkles className="w-4 h-4" />
            </span>
            Skill Issue
          </Link>
          <nav className="hidden md:flex items-center gap-7 text-sm text-slate-600">
            <a href="#features" className="hover:text-slate-900">Features</a>
            <a href="#code-reading" className="hover:text-slate-900">Code reading</a>
            <a href="#how" className="hover:text-slate-900">How it works</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login" className="text-sm text-slate-700 hover:text-slate-900 px-3 py-1.5">Sign in</Link>
            <Link to="/register" className="text-sm font-semibold bg-slate-900 text-white rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors">
              Start practicing
            </Link>
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="relative">
        <div
          className="absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_70%_0%,rgba(99,102,241,0.12),transparent),radial-gradient(40%_40%_at_10%_20%,rgba(16,185,129,0.08),transparent)]"
          aria-hidden
        />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-24 grid lg:grid-cols-2 gap-14 items-center">
          <div>
            <span className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-brand-700 bg-brand-50 border border-brand-100 rounded-full px-3 py-1 animate-fade-in">
              <Sparkles className="w-3.5 h-3.5" /> Interview practice that tells you the truth
            </span>
            <h1 className="mt-5 text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.05] animate-fade-up">
              Your interview went badly.{' '}
              <span className="bg-gradient-to-r from-brand-600 via-violet-500 to-emerald-500 bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient-pan">
                Good. Now we have data.
              </span>
            </h1>
            <p className="mt-5 text-lg text-slate-600 max-w-xl animate-fade-up" style={{ animationDelay: '120ms' }}>
              Mock interviews that sound like a real senior engineer: they push on your claims, interrupt your rambling and never call a
              vague answer great. Then you get evidence, a plan, and a re-test that proves whether you improved.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3 animate-fade-up" style={{ animationDelay: '220ms' }}>
              <Link
                to="/register"
                className="group inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold rounded-xl px-5 py-3 shadow-glow transition-all hover:-translate-y-0.5"
              >
                Take a mock interview <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a href="#code-reading" className="inline-flex items-center gap-1.5 text-slate-700 font-medium px-4 py-3 rounded-xl hover:bg-slate-50">
                Try a code-reading question <ChevronRight className="w-4 h-4" />
              </a>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-500 animate-fade-in" style={{ animationDelay: '400ms' }}>
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-600" /> No fake praise</span>
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-600" /> Audio never stored</span>
              <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-600" /> Findings quote your words</span>
            </div>
          </div>
          <div className="animate-fade-up" style={{ animationDelay: '200ms' }}>
            <HeroDemo />
          </div>
        </div>
      </section>

      {/* rounds marquee */}
      <section className="border-y border-slate-100 bg-slate-50/60 py-5 overflow-hidden" aria-label="Round types">
        <div className="flex w-max animate-marquee gap-10 pr-10">
          {[...ROUNDS, ...ROUNDS].map((r, i) => (
            <span key={i} className="flex items-center gap-2 text-sm font-medium text-slate-500 whitespace-nowrap">
              <Code2 className="w-4 h-4 text-brand-500" /> {r}
            </span>
          ))}
        </div>
      </section>

      {/* features */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <Reveal className="max-w-2xl">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Not another chatbot that asks questions.</h2>
          <p className="mt-3 text-slate-600 text-lg">Four things most prep tools skip, because they’re hard.</p>
        </Reveal>
        <div className="mt-12 grid sm:grid-cols-2 gap-5">
          {USPS.map((u, i) => (
            <Reveal key={u.title} delay={i * 90}>
              <div className="group h-full rounded-2xl border border-slate-200 bg-white p-6 hover:shadow-elevated hover:-translate-y-1 transition-all duration-300">
                <div className="w-11 h-11 rounded-xl bg-brand-50 text-brand-700 grid place-items-center group-hover:scale-110 group-hover:rotate-3 transition-transform">
                  <u.icon className="w-5 h-5" />
                </div>
                <h3 className="mt-4 text-lg font-semibold">{u.title}</h3>
                <p className="mt-2 text-slate-600 leading-relaxed">{u.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* code reading */}
      <section id="code-reading" className="bg-slate-950 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-24 grid lg:grid-cols-2 gap-12 items-center">
          <Reveal>
            <span className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-emerald-300">
              <Bug className="w-4 h-4" /> The round nobody prepares for
            </span>
            <h2 className="mt-3 text-3xl sm:text-4xl font-bold tracking-tight">Can you read code you didn’t write?</h2>
            <p className="mt-4 text-slate-300 text-lg leading-relaxed">
              Real codebases are read far more than they’re written. Our code-reading round hands you production-style code with
              planted bugs: caches, rate limiters, retries, pagination, consistent hashing. Explain it, trace it exactly, point at the
              line that breaks, and write the review comment.
            </p>
            <ul className="mt-6 space-y-2 text-slate-300">
              {['Trace answers checked against the code’s real output', 'Bug location checked to the line', 'Reviewer-style follow-ups that never give the answer away'].map((t) => (
                <li key={t} className="flex items-start gap-2"><CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" /> {t}</li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={120} className="text-slate-900">
            <CodeReadingDemo />
          </Reveal>
        </div>
      </section>

      {/* loop */}
      <section id="how" className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <Reveal className="text-center max-w-2xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">A loop, not a quiz.</h2>
          <p className="mt-3 text-slate-600 text-lg">Every session feeds the next one, until the numbers move.</p>
        </Reveal>
        <div className="mt-14 grid grid-cols-2 md:grid-cols-5 gap-6 relative">
          <div className="hidden md:block absolute top-7 left-[10%] right-[10%] h-px bg-gradient-to-r from-brand-200 via-brand-400 to-emerald-300" aria-hidden />
          {LOOP.map((s, i) => (
            <Reveal key={s.label} delay={i * 110} className="relative text-center">
              <div className="mx-auto w-14 h-14 rounded-2xl bg-white border border-slate-200 shadow-card grid place-items-center relative z-10">
                <s.icon className="w-6 h-6 text-brand-600" />
              </div>
              <div className="mt-3 font-semibold">{s.label}</div>
              <div className="text-sm text-slate-500">{s.sub}</div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* proof */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-24">
        <Reveal>
          <div className="rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-8 sm:p-10 grid md:grid-cols-3 gap-8">
            <div className="md:col-span-2">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-500">From a real session transcript</span>
              <div className="mt-4 space-y-3 text-[15px]">
                <p><b className="text-slate-500 font-medium">Candidate:</b> Redis made our API 10x faster.</p>
                <p><b className="text-brand-700 font-medium">Interviewer:</b> How did you measure that 10x speedup?</p>
                <p><b className="text-slate-500 font-medium">Candidate:</b> idk</p>
                <p><b className="text-brand-700 font-medium">Interviewer:</b> Say an endpoint suddenly takes 3 seconds. Where would you look first?</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <div className="text-3xl font-extrabold text-slate-900">4.1<span className="text-base text-slate-400">/5</span></div>
                <div className="text-sm text-slate-500">interviewer realism in our blind-judged eval suite</div>
              </div>
              <div>
                <div className="text-3xl font-extrabold text-slate-900">0</div>
                <div className="text-sm text-slate-500">“Great answer!”s across 10 scripted interviews</div>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* cta */}
      <section className="px-4 sm:px-6 pb-24">
        <Reveal>
          <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-br from-brand-600 via-brand-700 to-violet-700 bg-[length:200%_200%] animate-gradient-pan text-white p-10 sm:p-14 text-center shadow-elevated">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">Find out what’s actually holding you back.</h2>
            <p className="mt-3 text-brand-100 text-lg">One honest mock interview. Twenty minutes. Evidence you can act on.</p>
            <Link
              to="/register"
              className="mt-8 inline-flex items-center gap-2 bg-white text-brand-700 font-semibold rounded-xl px-6 py-3 hover:-translate-y-0.5 transition-transform"
            >
              Start practicing <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </Reveal>
      </section>

      <footer className="border-t border-slate-100 py-8 text-sm text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="font-semibold text-slate-700">Skill Issue</span>
          <span className="italic font-mono text-xs">“Your interview went badly. Good. Now we have data.”</span>
          <span>Scores are coaching signals, not hiring decisions.</span>
        </div>
      </footer>
    </div>
  );
};
