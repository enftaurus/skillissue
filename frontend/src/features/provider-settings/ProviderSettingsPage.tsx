import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { ProviderConfig, ModelMetadata } from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cloud,
  Cpu,
  ExternalLink,
  GraduationCap,
  Key,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

export const ProviderSettingsPage: React.FC = () => {
  const [config, setConfig] = useState<ProviderConfig | null>(null);
  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [providerName, setProviderName] = useState<'azure' | 'bedrock'>('azure');

  // AWS Bedrock State
  const [awsRegion, setAwsRegion] = useState('us-east-1');
  const [accessKeyId, setAccessKeyId] = useState('');
  const [secretAccessKey, setSecretAccessKey] = useState('');

  // Azure State
  const [azureEndpoint, setAzureEndpoint] = useState('');
  const [azureApiKey, setAzureApiKey] = useState('');
  const [azureApiVersion, setAzureApiVersion] = useState('2024-06-01');
  const [azureDeploymentName, setAzureDeploymentName] = useState('gpt-4o-mini');

  // Model Routing & Inference State
  const [preferredModel, setPreferredModel] = useState('azure.gpt-4.1-mini');
  const [interviewerModel, setInterviewerModel] = useState('azure.gpt-4.1-mini');
  const [evaluationModel, setEvaluationModel] = useState('azure.gpt-4.1');
  const [codingModel, setCodingModel] = useState('azure.gpt-4.1-mini');
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

        const currentProvider = (cfg.provider_name === 'azure' ? 'azure' : 'bedrock') as 'azure' | 'bedrock';
        setProviderName(currentProvider);

        // Bedrock fields
        setAwsRegion(cfg.aws_region || 'us-east-1');

        // Azure fields
        setAzureEndpoint(cfg.azure_endpoint || '');
        setAzureApiVersion(cfg.azure_api_version || '2024-06-01');
        setAzureDeploymentName(cfg.azure_deployment_name || 'gpt-4.1-mini');

        // Models
        if (currentProvider === 'azure') {
          setPreferredModel(cfg.preferred_model || 'azure.gpt-4.1-mini');
          setInterviewerModel(cfg.interviewer_model || cfg.preferred_model || 'azure.gpt-4.1-mini');
          setEvaluationModel(cfg.evaluation_model || 'azure.gpt-4.1');
          setCodingModel(cfg.coding_model || 'azure.gpt-4.1-mini');
        } else {
          setPreferredModel(cfg.preferred_model || 'qwen.qwen3-32b-v1:0');
          setInterviewerModel(cfg.interviewer_model || cfg.preferred_model || 'qwen.qwen3-32b-v1:0');
          setEvaluationModel(cfg.evaluation_model || 'us.deepseek.r1-v1:0');
          setCodingModel(cfg.coding_model || 'qwen.qwen3-coder-30b-a3b-v1:0');
        }

        setFallbackEnabled(Boolean(cfg.fallback_enabled));
        setFallbackProvider(cfg.fallback_provider || 'mock');
        setFallbackModel(cfg.fallback_model || (currentProvider === 'azure' ? 'mock-gpt-4o-mini' : 'mock-qwen3-32b'));
        setTemperature(cfg.temperature ?? 0.7);
        setMaxTokens(cfg.max_tokens ?? 1024);
      })
      .catch((err) => {
        setNotification({ type: 'error', message: err.message });
      })
      .finally(() => setLoading(false));
  }, []);

  const handleProviderSwitch = (newProvider: 'azure' | 'bedrock') => {
    setProviderName(newProvider);
    setTestResult(null);
    setNotification(null);

    if (newProvider === 'azure') {
      setPreferredModel('azure.gpt-4.1-mini');
      setInterviewerModel('azure.gpt-4.1-mini');
      setEvaluationModel('azure.gpt-4.1');
      setCodingModel('azure.gpt-4.1-mini');
      setFallbackModel('mock-gpt-4o-mini');
    } else {
      setPreferredModel('qwen.qwen3-32b-v1:0');
      setInterviewerModel('qwen.qwen3-32b-v1:0');
      setEvaluationModel('us.deepseek.r1-v1:0');
      setCodingModel('qwen.qwen3-coder-30b-a3b-v1:0');
      setFallbackModel('mock-qwen3-32b');
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const payload =
        providerName === 'azure'
          ? {
              provider_name: 'azure',
              azure_endpoint: azureEndpoint,
              azure_api_key: azureApiKey || undefined,
              azure_api_version: azureApiVersion,
              azure_deployment_name: azureDeploymentName,
              preferred_model: preferredModel,
            }
          : {
              provider_name: 'bedrock',
              aws_region: awsRegion,
              aws_access_key_id: accessKeyId || undefined,
              aws_secret_access_key: secretAccessKey || undefined,
              preferred_model: preferredModel,
            };

      const res = await api.post<{ success: boolean; message: string; latency_ms?: number }>('/providers/test', payload);
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
      const payload: any = {
        provider_name: providerName,
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
      };

      if (providerName === 'azure') {
        payload.azure_endpoint = azureEndpoint;
        if (azureApiKey) payload.azure_api_key = azureApiKey;
        payload.azure_api_version = azureApiVersion;
        payload.azure_deployment_name = azureDeploymentName;
      } else {
        payload.aws_region = awsRegion;
        if (accessKeyId) payload.aws_access_key_id = accessKeyId;
        if (secretAccessKey) payload.aws_secret_access_key = secretAccessKey;
      }

      const updated = await api.put<ProviderConfig>('/providers/config', payload);
      setConfig(updated);
      setAccessKeyId('');
      setSecretAccessKey('');
      setAzureApiKey('');
      setNotification({ type: 'success', message: `${providerName === 'azure' ? 'Azure OpenAI' : 'Amazon Bedrock'} configuration saved successfully.` });
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Failed to save configuration.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteCredentials = async () => {
    const cloudName = providerName === 'azure' ? 'Azure' : 'AWS';
    if (!window.confirm(`Are you sure you want to delete your stored ${cloudName} credentials? You will need to reconfigure before running further interviews.`)) {
      return;
    }
    try {
      const updated = await api.delete<ProviderConfig>('/providers/credentials');
      setConfig(updated);
      setNotification({ type: 'success', message: `Stored ${cloudName} credentials permanently deleted from the database.` });
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

  const activeProviderModels = models.filter((m) => {
    if (providerName === 'azure') return m.provider === 'azure';
    return m.provider === 'bedrock' || m.provider === 'mock';
  });

  const isConfiguredForActiveProvider =
    config?.provider_name === providerName && Boolean(config?.aws_access_key_masked);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Page Title & Context */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-lime-700" />
            AI Provider Settings (BYOC)
          </h1>
          <Link to="/onboarding/bedrock">
            <Button variant="outline" size="sm">
              <ExternalLink className="w-3.5 h-3.5" />
              Onboarding Wizard
            </Button>
          </Link>
        </div>
        <p className="mt-1 text-sm text-ink-muted">
          Connect your own cloud credentials (Azure OpenAI or Amazon Bedrock) with zero markup.
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
              Estimated Spend & Logged Tokens
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
              {providerName === 'azure'
                ? 'Using GPT-4o Mini ($0.15 / $0.60 per 1M tokens), a $100 student credit covers 1,000+ full interviews.'
                : 'Using Qwen3 32B ($0.1545 / $0.618 per 1M tokens), a $20 budget allows ~500+ full interviews.'}
            </p>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            <Badge variant={config?.provider_name === providerName ? 'lime' : 'zinc'}>
              Active: {config?.provider_name.toUpperCase()}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Provider Selector Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Azure Option */}
        <div
          onClick={() => handleProviderSwitch('azure')}
          className={`cursor-pointer rounded-xl p-4 border-2 transition-all flex flex-col justify-between ${
            providerName === 'azure'
              ? 'border-lime-600 bg-white shadow-sm ring-2 ring-lime-500/20'
              : 'border-surface-border bg-surface-card hover:border-ink-subtle/40'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center font-bold">
                <Cloud className="w-4 h-4" />
              </div>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-lime-100 text-lime-800">
                <GraduationCap className="w-3 h-3" />
                Recommended for Students
              </span>
            </div>
            <h3 className="text-base font-bold text-ink">Microsoft Azure (OpenAI)</h3>
            <p className="text-xs text-ink-muted mt-1 leading-relaxed">
              Fast setup with $100 free student credit. Direct access to GPT-4o Mini & GPT-4o.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-surface-border flex items-center justify-between text-xs font-medium">
            <span className="text-ink">GPT-4o Mini & GPT-4o</span>
            <span className={providerName === 'azure' ? 'text-lime-700 font-bold' : 'text-ink-muted'}>
              {providerName === 'azure' ? '✓ Selected' : 'Switch to Azure'}
            </span>
          </div>
        </div>

        {/* AWS Bedrock Option */}
        <div
          onClick={() => handleProviderSwitch('bedrock')}
          className={`cursor-pointer rounded-xl p-4 border-2 transition-all flex flex-col justify-between ${
            providerName === 'bedrock'
              ? 'border-lime-600 bg-white shadow-sm ring-2 ring-lime-500/20'
              : 'border-surface-border bg-surface-card hover:border-ink-subtle/40'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-700">
                Open-Weights BYOC
              </span>
            </div>
            <h3 className="text-base font-bold text-ink">Amazon Web Services (Bedrock)</h3>
            <p className="text-xs text-ink-muted mt-1 leading-relaxed">
              Direct access to open-weights models: Qwen 32B, DeepSeek-R1, and Amazon Nova.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-surface-border flex items-center justify-between text-xs font-medium">
            <span className="text-ink">Qwen 32B & DeepSeek-R1</span>
            <span className={providerName === 'bedrock' ? 'text-lime-700 font-bold' : 'text-ink-muted'}>
              {providerName === 'bedrock' ? '✓ Selected' : 'Switch to AWS'}
            </span>
          </div>
        </div>
      </div>

      {/* Cloud-Specific Budget Warning */}
      {providerName === 'azure' ? (
        <div className="rounded-xl border border-amber-300 bg-amber-50/70 p-4 flex gap-3 items-start">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 leading-relaxed">
            <strong className="font-semibold block text-amber-950 mb-0.5">
              Azure Student Account Budget Advisory:
            </strong>
            Remember to set a spending alert in <strong>Azure Portal → Cost Management + Billing → Budgets</strong> (e.g. at $20.00). This protects your $100 student credits and ensures uninterrupted access.
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-rose-300 bg-rose-50/70 p-4 flex gap-3 items-start">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-900 leading-relaxed">
            <strong className="font-semibold block text-rose-950 mb-0.5">
              AWS Credit Card Billing Advisory:
            </strong>
            AWS Bedrock token usage bills directly to your credit card. Create an alert in <strong>AWS Billing Console → Budgets</strong> (e.g. at $10.00) so you never encounter unexpected charges.
          </div>
        </div>
      )}

      {/* Main Configuration Form */}
      <Card>
        <form onSubmit={handleSave} className="space-y-6">
          {/* Credentials Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                {providerName === 'azure' ? 'Azure OpenAI Credentials & Endpoint' : 'AWS IAM Credentials & Region'}
              </span>
              <span className="text-xs text-ink-subtle flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-lime-700" />
                Encrypted at rest with AES-256
              </span>
            </div>

            {isConfiguredForActiveProvider && config?.aws_access_key_masked && (
              <div className="p-3 bg-surface-warm rounded-md border border-surface-border flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs">
                  <Key className="w-3.5 h-3.5 text-ink-subtle" />
                  <span>Saved Key:</span>
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

            {providerName === 'azure' ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-ink mb-1.5">
                    Azure OpenAI Endpoint URL <span className="text-rose-500">*</span>
                  </label>
                  <Input
                    type="text"
                    value={azureEndpoint}
                    onChange={(e) => setAzureEndpoint(e.target.value)}
                    placeholder="https://your-resource-name.openai.azure.com/"
                  />
                  <span className="text-[11px] text-ink-subtle mt-1 block">
                    Found under Keys and Endpoint in your Azure OpenAI resource.
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-medium text-ink mb-1.5">
                    {isConfiguredForActiveProvider ? 'Update Azure API Key (Leave blank to keep saved)' : 'Azure API Key'} <span className="text-rose-500">*</span>
                  </label>
                  <Input
                    type="password"
                    value={azureApiKey}
                    onChange={(e) => setAzureApiKey(e.target.value)}
                    placeholder={isConfiguredForActiveProvider ? '••••••••••••••••' : 'Paste Key 1 or Key 2'}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-ink mb-1.5">
                      Deployment Name (Optional)
                    </label>
                    <Input
                      type="text"
                      value={azureDeploymentName}
                      onChange={(e) => setAzureDeploymentName(e.target.value)}
                      placeholder="gpt-4.1-mini"
                    />
                    <span className="text-[11px] text-ink-subtle mt-1 block">
                      Name of your deployment in Azure OpenAI Studio.
                    </span>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-ink mb-1.5">
                      API Version
                    </label>
                    <Input
                      type="text"
                      value={azureApiVersion}
                      onChange={(e) => setAzureApiVersion(e.target.value)}
                      placeholder="2024-06-01"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
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
                      label={isConfiguredForActiveProvider ? "Update Access Key ID (Leave blank to keep saved)" : "AWS Access Key ID"}
                      type="text"
                      value={accessKeyId}
                      onChange={(e) => setAccessKeyId(e.target.value)}
                      placeholder="AKIA..."
                    />
                  </div>
                </div>

                <Input
                  label={isConfiguredForActiveProvider ? "Update Secret Access Key (Leave blank to keep saved)" : "AWS Secret Access Key"}
                  type="password"
                  value={secretAccessKey}
                  onChange={(e) => setSecretAccessKey(e.target.value)}
                  placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                />
              </div>
            )}

            {/* Test Results */}
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

          {/* Model Selection Lineup */}
          <div className="pt-4 border-t border-surface-border">
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
              Available Models ({providerName === 'azure' ? 'Azure OpenAI' : 'AWS Bedrock'})
            </label>
            <div className="space-y-2.5">
              {activeProviderModels.map((m) => {
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
                Task-Specific Routing
              </label>
              <p className="text-xs text-ink-subtle mt-1">
                Assign specialized models for interview dialogue, evaluations, and coding hints.
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
                  {activeProviderModels.map((m) => (
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
                  {activeProviderModels.map((m) => (
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
                  {activeProviderModels.map((m) => (
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
                  Gracefully route to a local mock when cloud rate limits or timeouts occur.
                </span>
              </div>
              <input
                type="checkbox"
                checked={fallbackEnabled}
                onChange={(e) => setFallbackEnabled(e.target.checked)}
                className="w-4 h-4 accent-lime-600 rounded"
              />
            </div>

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

          {/* Action Buttons */}
          <div className="pt-4 border-t border-surface-border flex items-center justify-between">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={handleTest}
              isLoading={isTesting}
            >
              Test Connection
            </Button>

            <Button type="submit" variant="primary" size="md" isLoading={isSaving}>
              Save Provider Configuration
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
