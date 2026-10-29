import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Sparkles } from 'lucide-react';

export const LoginPage: React.FC = () => {
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
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col justify-center items-center px-4 py-12 sm:px-6 lg:px-8 bg-surface-warm">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-lime-500/15 border border-lime-500/30 text-lime-700 mb-4">
          <Sparkles className="w-6 h-6 fill-lime-600/30" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-ink">Welcome back to Skill Issue</h2>
        <p className="mt-2 text-sm text-ink-muted">
          "Your interview went badly. Good. Now we have data."
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 text-xs bg-red-50 border border-red-200 text-red-700 rounded-md">
                {error}
              </div>
            )}

            <Input
              label="Email address"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@domain.com"
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
              Sign In
            </Button>
          </form>

          <div className="mt-6 pt-5 border-t border-surface-border text-center">
            <p className="text-xs text-ink-muted">
              Don't have an account?{' '}
              <Link to="/register" className="font-semibold text-lime-700 hover:text-lime-800">
                Register for free
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
