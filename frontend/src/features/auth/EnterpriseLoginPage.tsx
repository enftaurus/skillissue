import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Building2, ArrowRight } from 'lucide-react';

export const EnterpriseLoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      // Ensure user info refreshed, then route to enterprise portal
      navigate('/enterprise');
    } catch (err: any) {
      setError(err.message || 'Invalid enterprise recruiter credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col justify-center items-center px-4 py-12 sm:px-6 lg:px-8 bg-zinc-50/60">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-lime-50 border border-lime-200 text-lime-700 mb-4 shadow-xs">
          <Building2 className="w-6 h-6" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-zinc-900">
          Enterprise & TPO Portal
        </h2>
        <p className="mt-2 text-sm text-zinc-600 leading-relaxed">
          Screen candidates with multi-round pipelines: Custom OA DSA, AI Systems Take-Home, and Cross-Exam Technical Rounds.
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Card className="p-6 sm:p-8 rounded-2xl border border-zinc-200 shadow-xs bg-white">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 text-xs bg-red-50 border border-red-200 text-red-700 rounded-xl">
                {error}
              </div>
            )}

            <Input
              label="Work Email / Recruiter ID"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="recruiter@skillissue.com"
            />

            <Input
              label="Password"
              type="password"
              required
              showPasswordToggle
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />

            <Button type="submit" variant="primary" className="w-full mt-2" isLoading={loading}>
              Sign In as Recruiter <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </form>

          <div className="mt-6 pt-5 border-t border-zinc-100 flex flex-col gap-2 text-center">
            <p className="text-xs text-zinc-500">
              Candidate looking to practice?{' '}
              <Link to="/login" className="font-semibold text-lime-700 hover:text-lime-800 underline underline-offset-2">
                Candidate Login
              </Link>
            </p>
            <p className="text-xs text-zinc-400">
              Admin Console:{' '}
              <Link to="/admin/login" className="text-zinc-600 hover:text-zinc-800">
                /admin/login
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
