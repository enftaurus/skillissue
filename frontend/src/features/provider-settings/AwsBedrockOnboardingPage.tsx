import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { ModelMetadata, ProviderConfig } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import {
  ShieldCheck,
  Copy,
  Check,
  AlertCircle,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

interface IamPolicyResponse {
  policy_document: string;
  statement: any;
  models: string[];
  regions: string[];
}

export const AwsBedrockOnboardingPage: React.FC = () => {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  // Model & Region Selection
  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('qwen.qwen3-32b-v1:0');
  const [selectedRegion, setSelectedRegion] = useState<string>('us-east-1');

  // IAM Policy
  const [policyDoc, setPolicyDoc] = useState<string>('');
  const [policyCopied, setPolicyCopied] = useState(false);

  // Credentials
  const [accessKeyId, setAccessKeyId] = useState('');
  const [secretAccessKey, setSecretAccessKey] = useState('');
  const [sessionToken, setSessionToken] = useState('');

  // Validation & Saving
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms?: number } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load models on mount
  useEffect(() => {
    api
      .get<ModelMetadata[]>('/providers/models')
      .then((data) => {
        // Filter bedrock models
        const bedrockModels = data.filter((m) => m.provider === 'bedrock' || m.model_id.includes('.'));
        setModels(bedrockModels);
        const defaultModel = bedrockModels.find((m) => m.is_default) || bedrockModels[0];
        if (defaultModel) {
          setSelectedModel(defaultModel.model_id);
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load model catalog.');
      });
  }, []);

  // Fetch least-privilege IAM policy when model or region changes
  useEffect(() => {
    if (!selectedModel) return;
    api
      .get<IamPolicyResponse>(`/providers/iam-policy?models=${encodeURIComponent(selectedModel)}&regions=${encodeURIComponent(selectedRegion)}`)
      .then((res) => {
        setPolicyDoc(res.policy_document);
      })
      .catch(() => {
        // Fallback default policy if endpoint fails
        const fallback = {
          Version: '2012-10-17',
          Statement: [
            {
              Sid: 'SkillIssueBedrockInvocation',
              Effect: 'Allow',
              Action: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
              ],
              Resource: [
                `arn:aws:bedrock:${selectedRegion}::foundation-model/${selectedModel}`,
                `arn:aws:bedrock:${selectedRegion}:*:inference-profile/*`,
              ],
            },
          ],
        };
        setPolicyDoc(JSON.stringify(fallback, null, 2));
      });
  }, [selectedModel, selectedRegion]);

  const handleCopyPolicy = () => {
    navigator.clipboard.writeText(policyDoc);
    setPolicyCopied(true);
    setTimeout(() => setPolicyCopied(false), 2500);
  };

  const handleTestConnection = async () => {
    if (!accessKeyId.trim() || !secretAccessKey.trim()) {
      setError('Please provide your AWS Access Key ID and Secret Access Key before testing.');
      return;
    }
    setError(null);
    setIsTesting(true);
    setTestResult(null);

    try {
      const res = await api.post<{ success: boolean; message: string; latency_ms?: number }>('/providers/test', {
        provider_name: 'bedrock',
        aws_region: selectedRegion,
        aws_access_key_id: accessKeyId.trim(),
        aws_secret_access_key: secretAccessKey.trim(),
        aws_session_token: sessionToken.trim() || undefined,
        preferred_model: selectedModel,
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed. Check IAM permissions and model access in AWS Console.',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleCompleteSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessKeyId.trim() || !secretAccessKey.trim()) {
      setError('Please provide AWS credentials to complete setup.');
      return;
    }
    setIsSaving(true);
    setError(null);

    try {
      await api.put<ProviderConfig>('/providers/config', {
        provider_name: 'bedrock',
        aws_region: selectedRegion,
        aws_access_key_id: accessKeyId.trim(),
        aws_secret_access_key: secretAccessKey.trim(),
        aws_session_token: sessionToken.trim() || undefined,
        preferred_model: selectedModel,
        default_model: selectedModel,
        interviewer_model: selectedModel,
        evaluation_model: selectedModel,
        coding_model: selectedModel,
        planning_model: selectedModel,
        fallback_enabled: false,
      });

      await refreshUser();
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  const currentModelMeta = models.find((m) => m.model_id === selectedModel);

  return (
    <div className="max-w-3xl mx-auto py-10 px-4 sm:px-6 space-y-8">
      {/* Onboarding Header */}
      <div className="text-center sm:text-left">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-lime-100 text-lime-800 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Step 1 of 1: Bring Your Own Cloud (BYOC)</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          Connect your Amazon Bedrock Access
        </h1>
        <p className="mt-2 text-sm text-ink-muted leading-relaxed">
          Skill Issue connects directly to Amazon Bedrock using your own AWS account. You pay AWS raw token
          prices with zero markup. Your credentials are encrypted at rest with AES-256 and never logged or exposed.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-900 flex items-start gap-3 text-sm">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Setup Error</p>
            <p className="text-red-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Step 1: Model & Region Selection */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <h2 className="text-base font-bold text-ink flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-lime-100 text-lime-800 text-xs font-bold flex items-center justify-center">1</span>
            Select Primary Model & AWS Region
          </h2>
          <span className="text-xs text-ink-muted font-mono">Raw Bedrock Pricing</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              AWS Region
            </label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500"
            >
              <option value="us-east-1">us-east-1 (N. Virginia)</option>
              <option value="us-west-2">us-west-2 (Oregon)</option>
              <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
              <option value="ap-south-1">ap-south-1 (Mumbai)</option>
              <option value="ap-southeast-2">ap-southeast-2 (Sydney)</option>
            </select>
            <span className="text-[11px] text-ink-faint mt-1 block">
              Ensure model access is enabled for this Region in the AWS Bedrock Console.
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              Primary Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500 font-mono"
            >
              {models.map((m) => (
                <option key={m.model_id} value={m.model_id}>
                  {m.display_name} ({m.role})
                </option>
              ))}
            </select>
            <span className="text-[11px] text-ink-faint mt-1 block">
              Default: Amazon Nova Lite (fast, highly capable, ultra-low token cost).
            </span>
          </div>
        </div>

        {currentModelMeta && (
          <div className="p-3 bg-surface-subtle rounded-md border border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div>
              <span className="font-semibold text-ink">{currentModelMeta.display_name}</span>
              <p className="text-ink-subtle">{currentModelMeta.description}</p>
            </div>
            <div className="font-mono text-ink text-right shrink-0">
              <span className="font-bold text-lime-800">
                ${currentModelMeta.input_price_per_1m} / ${currentModelMeta.output_price_per_1m}
              </span>
              <span className="block text-[10px] text-ink-faint">per 1M input / output tokens</span>
            </div>
          </div>
        )}
      </Card>

      {/* Step 2: Least-Privilege IAM Policy */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <h2 className="text-base font-bold text-ink flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-lime-100 text-lime-800 text-xs font-bold flex items-center justify-center">2</span>
            Least-Privilege IAM Policy
          </h2>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopyPolicy}
            className="flex items-center gap-1.5 text-xs"
          >
            {policyCopied ? (
              <>
                <Check className="w-3.5 h-3.5 text-lime-600" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Policy JSON</span>
              </>
            )}
          </Button>
        </div>

        <p className="text-xs text-ink-muted">
          Paste this restricted policy into AWS IAM. It grants invocation rights strictly to your chosen model without granting administrative or unneeded AWS privileges.
        </p>

        <div className="relative">
          <pre className="p-3.5 bg-zinc-950 text-zinc-100 rounded-lg text-xs font-mono overflow-x-auto max-h-48 border border-zinc-800 leading-relaxed">
            {policyDoc || 'Generating policy...'}
          </pre>
        </div>

        <div className="p-3 bg-lime-50/50 rounded-md border border-lime-200 text-xs text-lime-900 space-y-1">
          <p className="font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-lime-700" />
            AWS Setup Instructions:
          </p>
          <ol className="list-decimal pl-5 space-y-0.5 text-lime-800">
            <li>In the AWS Console, open <strong>IAM &gt; Policies &gt; Create Policy</strong>.</li>
            <li>Click <strong>JSON</strong> tab, paste the policy above, and name it <code className="font-mono bg-white px-1 py-0.2 rounded border border-lime-300">SkillIssueBedrockPolicy</code>.</li>
            <li>Create an IAM User (e.g. <code className="font-mono bg-white px-1 py-0.2 rounded border border-lime-300">skillissue-user</code>) and attach this policy.</li>
            <li>Create an <strong>Access Key</strong> (Command Line Interface / Application) and paste the keys below.</li>
          </ol>
        </div>
      </Card>

      {/* Step 3: Enter & Validate Credentials */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <h2 className="text-base font-bold text-ink flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-lime-100 text-lime-800 text-xs font-bold flex items-center justify-center">3</span>
            Enter IAM Credentials & Verify
          </h2>
          <span className="text-xs text-ink-subtle flex items-center gap-1">
            <Lock className="w-3.5 h-3.5 text-lime-700" />
            AES-256 Encrypted
          </span>
        </div>

        <form onSubmit={handleCompleteSetup} className="space-y-4">
          <Input
            label="AWS Access Key ID"
            type="text"
            required
            value={accessKeyId}
            onChange={(e) => setAccessKeyId(e.target.value)}
            placeholder="AKIAIOSFODNN7EXAMPLE"
          />

          <Input
            label="AWS Secret Access Key"
            type="password"
            required
            value={secretAccessKey}
            onChange={(e) => setSecretAccessKey(e.target.value)}
            placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
          />

          <Input
            label="AWS Session Token (Optional - only for temporary STS credentials)"
            type="password"
            value={sessionToken}
            onChange={(e) => setSessionToken(e.target.value)}
            placeholder="AQoDYXdzEJr1... (leave blank for standard IAM users)"
          />

          {testResult && (
            <div
              className={`p-3 rounded-md text-xs flex items-center justify-between border ${
                testResult.success
                  ? 'bg-lime-50 border-lime-200 text-lime-900'
                  : 'bg-red-50 border-red-200 text-red-900'
              }`}
            >
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="w-4 h-4 text-lime-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                )}
                <span>{testResult.message}</span>
              </div>
              {testResult.latency_ms && (
                <span className="font-mono font-semibold shrink-0 ml-2">{testResult.latency_ms}ms</span>
              )}
            </div>
          )}

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={handleTestConnection}
              isLoading={isTesting}
              disabled={!accessKeyId.trim() || !secretAccessKey.trim()}
              className="w-full sm:w-auto"
            >
              Test Bedrock Connection
            </Button>

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSaving}
              disabled={!accessKeyId.trim() || !secretAccessKey.trim()}
              className="w-full sm:w-auto flex items-center justify-center gap-2"
            >
              <span>Save & Launch Skill Issue</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};
