import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';

import { LoginPage } from './features/auth/LoginPage';
import { RegisterPage } from './features/auth/RegisterPage';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { InterviewSetupPage } from './features/interview-setup/InterviewSetupPage';
import { InterviewSessionPage } from './features/interview-session/InterviewSessionPage';
import { EvaluationPage } from './features/evaluation/EvaluationPage';
import { PlanlyPage } from './features/improvement-plan/PlanlyPage';
import { ProgressAnalyticsPage } from './features/progress/ProgressAnalyticsPage';
import { CodingPracticePage } from './features/coding/CodingPracticePage';
import { ProviderSettingsPage } from './features/provider-settings/ProviderSettingsPage';
import { AwsSetupGuidePage } from './features/provider-settings/AwsSetupGuidePage';
import { AwsBedrockOnboardingPage } from './features/provider-settings/AwsBedrockOnboardingPage';

import { Sidebar } from './components/layout/Sidebar';
import { CommandPalette } from './components/layout/CommandPalette';
import { CreditsUsageBadge } from './components/layout/CreditsUsageBadge';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mb-3" />
        <span className="text-xs text-ink-muted">Authenticating...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (
    user.onboarding_completed === false &&
    !user.is_provider_connected &&
    location.pathname !== '/onboarding/bedrock' &&
    location.pathname !== '/docs/aws-bedrock-setup'
  ) {
    return <Navigate to="/onboarding/bedrock" replace />;
  }

  return <>{children}</>;
};

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const location = useLocation();
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('skillissue_sidebar_collapsed') === 'true';
  });

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('skillissue_sidebar_collapsed', String(next));
      return next;
    });
  };

  const isAuthRoute =
    location.pathname === '/login' ||
    location.pathname === '/register' ||
    location.pathname === '/onboarding/bedrock';

  const isInterviewSession =
    location.pathname.startsWith('/interviews/') && location.pathname !== '/interviews/new';

  if (!user || isAuthRoute) {
    return (
      <div className="min-h-screen flex flex-col bg-surface-warm font-sans text-ink">
        <main className="flex-1 flex flex-col">{children}</main>
      </div>
    );
  }

  // Interview Focus Mode: zero distraction, no sidebar, locked to interview room
  if (isInterviewSession) {
    return (
      <div className="min-h-screen flex flex-col bg-surface-warm font-sans text-ink">
        <main className="flex-1 flex flex-col">{children}</main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-surface-warm font-sans text-ink">
      <Sidebar
        onOpenCommandPalette={() => setIsPaletteOpen(true)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-200 ${
          isSidebarCollapsed ? 'pl-16' : 'pl-60'
        }`}
      >
        <main className="flex-1 pb-16">{children}</main>
        <footer className="border-t border-surface-border bg-white py-3.5 px-6">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-muted">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink">Skill Issue</span>
              <span>•</span>
              <span className="italic font-mono text-[11px]">&ldquo;Your interview went badly. Good. Now we have data.&rdquo;</span>
            </div>
            <div className="flex items-center gap-3 text-ink-subtle">
              <CreditsUsageBadge />
              <span>•</span>
              <button
                onClick={() => setIsPaletteOpen(true)}
                className="hover:text-ink font-mono text-[11px] px-2 py-0.5 rounded bg-surface-subtle border border-surface-border"
              >
                ⌘K Palette
              </button>
              <span>•</span>
              <span>Strict Light Theme</span>
            </div>
          </div>
        </footer>
      </div>
      <CommandPalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} />
    </div>
  );
};


export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected Core Application Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/interviews/new"
              element={
                <ProtectedRoute>
                  <InterviewSetupPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/interviews/:id"
              element={
                <ProtectedRoute>
                  <InterviewSessionPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/evaluations/:id"
              element={
                <ProtectedRoute>
                  <EvaluationPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/planly"
              element={
                <ProtectedRoute>
                  <PlanlyPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/progress"
              element={
                <ProtectedRoute>
                  <ProgressAnalyticsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/coding"
              element={
                <ProtectedRoute>
                  <CodingPracticePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings/provider"
              element={
                <ProtectedRoute>
                  <ProviderSettingsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/docs/aws-bedrock-setup"
              element={
                <ProtectedRoute>
                  <AwsSetupGuidePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/onboarding/bedrock"
              element={
                <ProtectedRoute>
                  <AwsBedrockOnboardingPage />
                </ProtectedRoute>
              }
            />

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </AuthProvider>
  );
};
export default App;
