import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { ProviderConfig, ModelMetadata } from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { AlertCircle, CheckCircle2, Cpu, ExternalLink, Key, ShieldCheck, Trash2 } from 'lucide-react';

export const ProviderSettingsPage: React.FC = () => {
  const [config, setConfig] = useState<ProviderConfig | null>(null);
  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [providerName, setProviderName] = useState<'bedrock' | 'mock'>('mock');
  const [awsRegion, setAwsRegion] = useState('us-east-1');
  const [accessKeyId, setAccessKeyId] = useState('');
  const [secretAccessKey, setSecretAccessKey] = useState('');
  const [preferredModel, setPreferredModel] = useState('qwen.qwen3-32b-instruct-v1:0');
  const [interviewerModel, setInterviewerModel] = useState('');
  const [evaluationModel, setEvaluationModel] = useState('');
  const [codingModel, setCodingModel] = useState('');
  const [fallbackEnabled, setFallbackEnabled] = useState(false);
  const [fallbackProvider, setFallbackProvider] = useState('mock');
  const [fallbackModel, setFallbackModel] = useState('mock-qwen3-32b');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1024);

  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms?: number } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<ProviderConfig>('/providers/config'),
      api.get<ModelMetadata[]>('/providers/models')
    ])
      .then(([cfg, modelList]) => {
        setConfig(cfg);
        setModels(modelList);
        setProviderName(cfg.provider_name as 'bedrock' | 'mock');
        setAwsRegion(cfg.aws_region || 'us-east-1');
        setPreferredModel(cfg.preferred_model || 'qwen.qwen3-32b-instruct-v1:0');
        setInterviewerModel(cfg.interviewer_model || cfg.preferred_model || 'qwen.qwen3-32b-instruct-v1:0');
        setEvaluationModel(cfg.evaluation_model || 'qwen.qwen3-next-80b-instruct-v1:0');
        setCodingModel(cfg.coding_model || 'qwen.qwen3-coder-30b-instruct-v1:0');
        setFallbackEnabled(Boolean(cfg.fallback_enabled));
        setFallbackProvider(cfg.fallback_provider || 'mock');
        setFallbackModel(cfg.fallback_model || 'mock-qwen3-32b');
        setTemperature(cfg.temperature ?? 0.7);
        setMaxTokens(cfg.max_tokens ?? 1024);
      })
      .catch((err) => {
        setNotification({ type: 'error', message: err.message });
      })
      .finally(() => setLoading(false));
  }, []);

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await api.post<{ success: boolean; message: string; latency_ms?: number }>('/providers/test', {
        provider_name: providerName,
        aws_region: awsRegion,
        aws_access_key_id: accessKeyId,
        aws_secret_access_key: secretAccessKey,
        preferred_model: preferredModel,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Connection test failed' });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setNotification(null);

    try {
      const updated = await api.put<ProviderConfig>('/providers/config', {
        provider_name: providerName,
        aws_region: awsRegion,
        aws_access_key_id: accessKeyId || undefined,
        aws_secret_access_key: secretAccessKey || undefined,
        preferred_model: preferredModel,
        default_model: preferredModel,
        interviewer_model: interviewerModel,
        evaluation_model: evaluationModel,
        coding_model: codingModel,
        fallback_enabled: fallbackEnabled,
        fallback_provider: fallbackProvider,
        fallback_model: fallbackModel,
        temperature,
        max_tokens: maxTokens,
      });
      setConfig(updated);
      setAccessKeyId('');
      setSecretAccessKey('');
      setNotification({ type: 'success', message: 'Provider configuration and task routing saved successfully.' });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to save configuration.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteCredentials = async () => {
    if (!window.confirm('Are you sure you want to delete your stored AWS credentials? You will need to reconfigure Bedrock before running further interviews or coaching sessions.')) {
      return;
    }
    try {
      const updated = await api.delete<ProviderConfig>('/providers/credentials');
      setConfig(updated);
      setNotification({ type: 'success', message: 'Stored AWS credentials permanently deleted from the database.' });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message });
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="inline-block animate-spin w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full" />
        <p className="mt-3 text-sm text-ink-muted">Loading provider settings...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Page Title & Context */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-lime-700" />
            AI Provider Settings (BYOC)
          </h1>
          <Link to="/docs/aws-bedrock-setup">
            <Button variant="outline" size="sm">
              <ExternalLink className="w-3.5 h-3.5" />
              AWS Setup Guide
            </Button>
          </Link>
        </div>
        <p className="mt-1 text-sm text-ink-muted">
          Connect your own Amazon Bedrock cloud credentials with zero markup, or run in offline mock mode.
        </p>
      </div>

      {notification && (
        <div
          className={`p-4 rounded-lg flex items-start gap-3 border ${
            notification.type === 'success'
              ? 'bg-lime-50 border-lime-200 text-lime-900'
              : 'bg-red-50 border-red-200 text-red-900'
          }`}
        >
          {notification.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-lime-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          )}
          <p className="text-sm font-medium">{notification.message}</p>
        </div>
      )}

      {/* Usage & Budget Tracking Card */}
      <Card className="bg-surface-warm border-lime-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-lime-800">
              $20 Planning Budget Headroom
            </span>
            <div className="mt-1 flex items-baseline gap-3">
              <span className="text-2xl font-bold text-ink">
                ${config?.estimated_cost_usd?.toFixed(4) || '0.0000'}
              </span>
              <span className="text-xs text-ink-muted">
                estimated spend ({config?.total_tokens_used?.toLocaleString() || 0} tokens logged)
              </span>
            </div>
            <p className="text-xs text-ink-subtle mt-1">
              At Qwen3 32B rates ($0.1545 / $0.618 per 1M tokens), a $20 budget allows ~500+ full interviews.
            </p>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            <Badge variant={config?.provider_name === 'bedrock' ? 'lime' : 'zinc'}>
              Mode: {config?.provider_name.toUpperCase()}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Configuration Form */}
      <Card>
        <form onSubmit={handleSave} className="space-y-6">
          {/* Provider Info */}
          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
              Inference Provider
            </label>
            <div className="p-4 rounded-lg border border-lime-600 bg-lime-50/30 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-ink">Amazon Bedrock (BYOC)</span>
                  <Badge variant="lime" size="sm">Active</Badge>
                </div>
                <p className="text-xs text-ink-subtle mt-1">
                  Live AI inference via your secure AWS IAM credentials. Pay AWS token prices directly with zero markup.
                </p>
              </div>
              <Link to="/docs/aws-bedrock-setup">
                <Button variant="outline" size="sm" type="button">
                  Setup Docs
                </Button>
              </Link>
            </div>
          </div>

          {/* Model Selection Lineup */}
          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
              Recommended Model Lineup
            </label>
            <div className="space-y-2.5">
              {models.map((m) => {
                const isSelected = preferredModel === m.model_id;
                return (
                  <label
                    key={m.model_id}
                    className={`block p-3.5 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-lime-600 bg-lime-50/40 ring-1 ring-lime-600'
                        : 'border-surface-border hover:bg-surface-subtle'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="model"
                          checked={isSelected}
                          onChange={() => setPreferredModel(m.model_id)}
                          className="accent-lime-600 mt-0.5"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-ink">{m.display_name}</span>
                            <Badge variant={m.is_default ? 'lime' : 'zinc'} size="sm">
                              {m.role}
                            </Badge>
                          </div>
                          <p className="text-xs text-ink-subtle mt-1">{m.description}</p>
                        </div>
                      </div>
                      <div className="text-right text-xs shrink-0 ml-4 font-mono">
                        {m.input_price_per_1m > 0 ? (
                          <>
                            <span className="text-ink font-semibold">
                              ${m.input_price_per_1m} / ${m.output_price_per_1m}
                            </span>
                            <span className="block text-[10px] text-ink-faint">per 1M tokens</span>
                          </>
                        ) : (
                          <span className="text-lime-700 font-semibold">Free (Offline)</span>
                        )}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Task-Specific Model Routing */}
          <div className="pt-4 border-t border-surface-border space-y-4">
            <div>
              <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider">
                Task-Specific Routing (LangGraph Orchestration)
              </label>
              <p className="text-xs text-ink-subtle mt-1">
                Assign specialized models for specific stages in your preparation loop.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-ink mb-1.5">
                  Interviewer Model
                </label>
                <select
                  value={interviewerModel}
                  onChange={(e) => setInterviewerModel(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500 font-mono"
                >
                  {models.map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-ink-faint mt-1 block">Dynamic dialogue & follow-ups</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1.5">
                  Evaluator Model
                </label>
                <select
                  value={evaluationModel}
                  onChange={(e) => setEvaluationModel(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500 font-mono"
                >
                  {models.map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-ink-faint mt-1 block">Deterministic scoring & rubric critique</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1.5">
                  Coding Specialist
                </label>
                <select
                  value={codingModel}
                  onChange={(e) => setCodingModel(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500 font-mono"
                >
                  {models.map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-ink-faint mt-1 block">Syntax, hints & algorithmic analysis</span>
              </div>
            </div>
          </div>

          {/* Fallback & Inference Controls */}
          <div className="pt-4 border-t border-surface-border space-y-4">
            <span className="block text-xs font-semibold text-ink-muted uppercase tracking-wider">
              Resilience & Inference Controls
            </span>

            <div className="flex items-center justify-between p-3 bg-surface-warm rounded-md border border-surface-border">
              <div>
                <span className="text-sm font-medium text-ink block">Automatic Provider Fallback</span>
                <span className="text-xs text-ink-subtle">
                  Gracefully route to a secondary model or local mock when cloud rate limits or timeouts occur.
                </span>
              </div>
              <input
                type="checkbox"
                checked={fallbackEnabled}
                onChange={(e) => setFallbackEnabled(e.target.checked)}
                className="w-4 h-4 accent-lime-600 rounded"
              />
            </div>

            {fallbackEnabled && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3 bg-surface-subtle rounded-md border border-surface-border">
                <div>
                  <label className="block text-xs font-medium text-ink mb-1.5">Fallback Provider</label>
                  <select
                    value={fallbackProvider}
                    onChange={(e) => setFallbackProvider(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink"
                  >
                    <option value="mock">Local Mock Provider (Zero Cost)</option>
                    <option value="bedrock">Amazon Bedrock</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink mb-1.5">Fallback Model</label>
                  <input
                    type="text"
                    value={fallbackModel}
                    onChange={(e) => setFallbackModel(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink font-mono"
                    placeholder="mock-qwen3-32b"
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-medium text-ink">Sampling Temperature</label>
                  <span className="text-xs font-mono font-semibold text-lime-700">{temperature}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-lime-600"
                />
                <span className="text-[10px] text-ink-faint block mt-1">Lower = more deterministic, higher = more creative</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1.5">Max Generation Tokens</label>
                <input
                  type="number"
                  min={256}
                  max={4096}
                  step={128}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value) || 1024)}
                  className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink font-mono"
                />
                <span className="text-[10px] text-ink-faint block mt-1">Bounded between 256 and 4096 tokens</span>
              </div>
            </div>
          </div>

          {/* Bedrock IAM Credentials (Only visible when Bedrock is selected) */}
          {providerName === 'bedrock' && (
            <div className="pt-4 border-t border-surface-border space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                  AWS IAM Credentials & Region
                </span>
                <span className="text-xs text-ink-subtle flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-lime-700" />
                  Encrypted at rest with AES-256
                </span>
              </div>

              {config?.aws_access_key_masked && (
                <div className="p-3 bg-surface-warm rounded-md border border-surface-border flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs">
                    <Key className="w-3.5 h-3.5 text-ink-subtle" />
                    <span>Saved Access Key:</span>
                    <code className="font-mono font-semibold bg-white px-2 py-0.5 rounded border border-surface-border">
                      {config.aws_access_key_masked}
                    </code>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleDeleteCredentials}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                    Purge Credentials
                  </Button>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-1">
                  <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
                    AWS Region
                  </label>
                  <select
                    value={awsRegion}
                    onChange={(e) => setAwsRegion(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500"
                  >
                    <option value="us-east-1">us-east-1 (N. Virginia)</option>
                    <option value="us-west-2">us-west-2 (Oregon)</option>
                    <option value="ap-south-1">ap-south-1 (Mumbai)</option>
                    <option value="ap-southeast-2">ap-southeast-2 (Sydney)</option>
                    <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <Input
                    label={config?.aws_access_key_masked ? "Update Access Key ID (Leave blank to keep saved)" : "AWS Access Key ID"}
                    type="text"
                    value={accessKeyId}
                    onChange={(e) => setAccessKeyId(e.target.value)}
                    placeholder="AKIA..."
                  />
                </div>
              </div>

              <Input
                label={config?.aws_access_key_masked ? "Update Secret Access Key (Leave blank to keep saved)" : "AWS Secret Access Key"}
                type="password"
                value={secretAccessKey}
                onChange={(e) => setSecretAccessKey(e.target.value)}
                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
              />

              {/* Live Test Results */}
              {testResult && (
                <div
                  className={`p-3 rounded-md text-xs flex items-center justify-between border ${
                    testResult.success
                      ? 'bg-lime-50 border-lime-200 text-lime-900'
                      : 'bg-red-50 border-red-200 text-red-900'
                  }`}
                >
                  <span>{testResult.message}</span>
                  {testResult.latency_ms && (
                    <span className="font-mono font-semibold">{testResult.latency_ms}ms</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="pt-4 border-t border-surface-border flex items-center justify-between">
            {providerName === 'bedrock' && (accessKeyId || config?.aws_access_key_masked) ? (
              <Button
                type="button"
                variant="secondary"
                size="md"
                onClick={handleTest}
                isLoading={isTesting}
              >
                Test Connection
              </Button>
            ) : <div />}

            <Button type="submit" variant="primary" size="md" isLoading={isSaving}>
              Save Provider Configuration
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
