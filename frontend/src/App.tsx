import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';
import { Navbar } from './components/layout/Navbar';
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

  return <>{children}</>;
};

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-surface-warm font-sans text-ink">
      <Navbar />
      <main className="flex-1 pb-16">{children}</main>
      <footer className="border-t border-surface-border bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-muted">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-ink">Skill Issue</span>
            <span>•</span>
            <span className="italic font-mono text-[11px]">&ldquo;Your interview went badly. Good. Now we have data.&rdquo;</span>
          </div>
          <div className="flex items-center gap-4 text-ink-subtle">
            <a href="/docs/aws-bedrock-setup" className="hover:text-ink transition-colors">
              AWS Bedrock Guide
            </a>
            <span>•</span>
            <span>Light Theme Strict</span>
            <span>•</span>
            <span>BYOC Ready</span>
          </div>
        </div>
      </footer>
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

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </AuthProvider>
  );
};
export default App;
