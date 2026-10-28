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
  Cloud,
  GraduationCap,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react';

interface IamPolicyResponse {
  policy_json?: string;
  policy_document?: string;
  model_id: string;
  region: string;
}

export const ProviderOnboardingPage: React.FC = () => {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  // Active Provider Selection ('azure' or 'bedrock')
  const [providerType, setProviderType] = useState<'azure' | 'bedrock'>('azure');

  // Model Catalogs
  const [models, setModels] = useState<ModelMetadata[]>([]);
  const azureModels = models.filter((m) => m.provider === 'azure');
  const bedrockModels = models.filter((m) => m.provider === 'bedrock');

  // Azure State
  const [azureEndpoint, setAzureEndpoint] = useState('');
  const [azureApiKey, setAzureApiKey] = useState('');
  const [azureApiVersion, setAzureApiVersion] = useState('2024-06-01');
  const [azureDeploymentName, setAzureDeploymentName] = useState('gpt-4o-mini');
  const [azureSelectedModel, setAzureSelectedModel] = useState('azure.gpt-4o-mini');

  // AWS Bedrock State
  const [bedrockModel, setBedrockModel] = useState('qwen.qwen3-32b-v1:0');
  const [bedrockRegion, setBedrockRegion] = useState('us-east-1');
  const [awsAccessKeyId, setAwsAccessKeyId] = useState('');
  const [awsSecretAccessKey, setAwsSecretAccessKey] = useState('');
  const [awsSessionToken, setAwsSessionToken] = useState('');
  const [policyDoc, setPolicyDoc] = useState<string>('');
  const [policyCopied, setPolicyCopied] = useState(false);

  // Testing & Saving State
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms?: number } | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load models on mount
  useEffect(() => {
    api
      .get<ModelMetadata[]>('/providers/models')
      .then((data) => {
        setModels(data);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load model catalog.');
      });
  }, []);

  // Fetch IAM policy when Bedrock model/region changes
  useEffect(() => {
    if (providerType !== 'bedrock') return;
    api
      .get<IamPolicyResponse>(`/providers/iam-policy?model_id=${encodeURIComponent(bedrockModel)}&region=${encodeURIComponent(bedrockRegion)}`)
      .then((res) => {
        const doc = res.policy_document || res.policy_json;
        if (doc) setPolicyDoc(doc);
      })
      .catch(() => {
        const fallback = {
          Version: '2012-10-17',
          Statement: [
            {
              Sid: 'SkillIssueBedrockInvocation',
              Effect: 'Allow',
              Action: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
              Resource: [`arn:aws:bedrock:${bedrockRegion}::foundation-model/${bedrockModel}`],
            },
          ],
        };
        setPolicyDoc(JSON.stringify(fallback, null, 2));
      });
  }, [providerType, bedrockModel, bedrockRegion]);

  const handleCopyPolicy = () => {
    navigator.clipboard.writeText(policyDoc);
    setPolicyCopied(true);
    setTimeout(() => setPolicyCopied(false), 2500);
  };

  const handleTestConnection = async () => {
    setError(null);
    setTestResult(null);

    if (providerType === 'azure') {
      if (!azureEndpoint.trim() || !azureApiKey.trim()) {
        setError('Please provide your Azure Endpoint URL and API Key before testing.');
        return;
      }
    } else {
      if (!awsAccessKeyId.trim() || !awsSecretAccessKey.trim()) {
        setError('Please provide your AWS Access Key ID and Secret Access Key before testing.');
        return;
      }
    }

    setIsTesting(true);

    try {
      const payload =
        providerType === 'azure'
          ? {
              provider_name: 'azure',
              azure_endpoint: azureEndpoint.trim(),
              azure_api_key: azureApiKey.trim(),
              azure_api_version: azureApiVersion.trim() || '2024-06-01',
              azure_deployment_name: azureDeploymentName.trim() || undefined,
              preferred_model: azureSelectedModel,
            }
          : {
              provider_name: 'bedrock',
              aws_region: bedrockRegion,
              aws_access_key_id: awsAccessKeyId.trim(),
              aws_secret_access_key: awsSecretAccessKey.trim(),
              aws_session_token: awsSessionToken.trim() || undefined,
              preferred_model: bedrockModel,
            };

      const res = await api.post<{ success: boolean; message: string; latency_ms?: number }>('/providers/test', payload);
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed. Check your cloud permissions and endpoint URL.',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleCompleteSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (providerType === 'azure') {
      if (!azureEndpoint.trim() || !azureApiKey.trim()) {
        setError('Azure Endpoint URL and API Key are required.');
        return;
      }
    } else {
      if (!awsAccessKeyId.trim() || !awsSecretAccessKey.trim()) {
        setError('AWS Access Key ID and Secret Access Key are required.');
        return;
      }
    }

    setIsSaving(true);

    try {
      const payload =
        providerType === 'azure'
          ? {
              provider_name: 'azure',
              azure_endpoint: azureEndpoint.trim(),
              azure_api_key: azureApiKey.trim(),
              azure_api_version: azureApiVersion.trim() || '2024-06-01',
              azure_deployment_name: azureDeploymentName.trim() || undefined,
              preferred_model: azureSelectedModel,
              default_model: azureSelectedModel,
              interviewer_model: 'azure.gpt-4o-mini',
              evaluation_model: 'azure.gpt-4o',
              coding_model: 'azure.gpt-4o-mini',
              planning_model: 'azure.gpt-4o-mini',
              fallback_enabled: false,
            }
          : {
              provider_name: 'bedrock',
              aws_region: bedrockRegion,
              aws_access_key_id: awsAccessKeyId.trim(),
              aws_secret_access_key: awsSecretAccessKey.trim(),
              aws_session_token: awsSessionToken.trim() || undefined,
              preferred_model: bedrockModel,
              default_model: bedrockModel,
              interviewer_model: bedrockModel,
              evaluation_model: 'us.deepseek.r1-v1:0',
              coding_model: 'qwen.qwen3-coder-30b-a3b-v1:0',
              planning_model: bedrockModel,
              fallback_enabled: false,
            };

      await api.put<ProviderConfig>('/providers/config', payload);
      await refreshUser();
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 space-y-8">
      {/* Header */}
      <div className="text-center sm:text-left">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lime-100 text-lime-800 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Step 1 of 1: Bring Your Own Cloud (BYOC)</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">
          Connect Your Cloud Provider
        </h1>
        <p className="mt-2 text-sm text-ink-muted max-w-2xl">
          Skill Issue operates with zero markups directly against your cloud account. Your API keys are encrypted at rest with AES-256 and never logged.
        </p>
      </div>

      {/* Cloud Selection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Azure Option */}
        <div
          onClick={() => {
            setProviderType('azure');
            setTestResult(null);
            setError(null);
          }}
          className={`cursor-pointer rounded-xl p-5 border-2 transition-all flex flex-col justify-between ${
            providerType === 'azure'
              ? 'border-lime-600 bg-white shadow-sm ring-2 ring-lime-500/20'
              : 'border-surface-border bg-surface-card hover:border-ink-subtle/40'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center font-bold">
                <Cloud className="w-5 h-5" />
              </div>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-lime-100 text-lime-800">
                <GraduationCap className="w-3.5 h-3.5" />
                Recommended for Students
              </span>
            </div>
            <h3 className="text-lg font-bold text-ink">Microsoft Azure (OpenAI)</h3>
            <p className="text-xs text-ink-muted mt-1 leading-relaxed">
              Ideal for students. Use your free <strong>$100 student credits</strong> (no credit card required via GitHub Student Pack). Access GPT-4o Mini & GPT-4o instantly.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs font-medium text-ink">
            <span>GPT-4o Mini & GPT-4o</span>
            <span className={providerType === 'azure' ? 'text-lime-700 font-bold' : 'text-ink-muted'}>
              {providerType === 'azure' ? '✓ Selected' : 'Select'}
            </span>
          </div>
        </div>

        {/* AWS Bedrock Option */}
        <div
          onClick={() => {
            setProviderType('bedrock');
            setTestResult(null);
            setError(null);
          }}
          className={`cursor-pointer rounded-xl p-5 border-2 transition-all flex flex-col justify-between ${
            providerType === 'bedrock'
              ? 'border-lime-600 bg-white shadow-sm ring-2 ring-lime-500/20'
              : 'border-surface-border bg-surface-card hover:border-ink-subtle/40'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-100 text-zinc-700">
                Open-Weights BYOC
              </span>
            </div>
            <h3 className="text-lg font-bold text-ink">Amazon Web Services (Bedrock)</h3>
            <p className="text-xs text-ink-muted mt-1 leading-relaxed">
              Run open-weights models like Qwen 32B, DeepSeek-R1, and Amazon Nova via IAM programmatic access keys.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-surface-border flex items-center justify-between text-xs font-medium text-ink">
            <span>Qwen 32B & DeepSeek-R1</span>
            <span className={providerType === 'bedrock' ? 'text-lime-700 font-bold' : 'text-ink-muted'}>
              {providerType === 'bedrock' ? '✓ Selected' : 'Select'}
            </span>
          </div>
        </div>
      </div>

      {/* Cloud-Specific Linking Form */}
      {providerType === 'azure' ? (
        <div className="space-y-6">
          {/* Azure Instructions */}
          <Card className="border-l-4 border-l-sky-500 space-y-3">
            <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-800 text-xs font-bold flex items-center justify-center">1</span>
              Quick Azure Linking Guide (3 Minutes)
            </h3>
            <ol className="text-xs text-ink-muted space-y-1.5 list-decimal pl-5">
              <li>
                Open the <a href="https://portal.azure.com" target="_blank" rel="noreferrer" className="text-sky-700 underline font-medium inline-flex items-center gap-0.5">Azure Portal <ExternalLink className="w-3 h-3" /></a> with your student account.
              </li>
              <li>
                Search for <strong>Azure OpenAI</strong> and create or select an existing resource.
              </li>
              <li>
                In <strong>Azure OpenAI Studio</strong>, deploy <strong><code>gpt-4o-mini</code></strong> and <strong><code>gpt-4o</code></strong> under Deployments.
              </li>
              <li>
                Go to <strong>Resource Management → Keys and Endpoint</strong> in your Azure OpenAI resource and copy your Endpoint URL and Key.
              </li>
            </ol>
          </Card>

          {/* Azure Budget Warning Banner */}
          <div className="rounded-xl border border-amber-300 bg-amber-50/70 p-4 flex gap-3 items-start">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900 leading-relaxed">
              <strong className="font-semibold block text-amber-950 mb-0.5">
                Important Student Budget Protection:
              </strong>
              Azure student accounts receive a $100 credit. Make sure to set a spending alert in <strong>Azure Portal → Cost Management + Billing → Budgets</strong> (e.g. set a warning at $20.00). That way, Azure emails you before your credits deplete.
            </div>
          </div>

          {/* Azure Form */}
          <Card className="space-y-5">
            <h3 className="text-base font-semibold text-ink">Azure OpenAI Credentials</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Azure OpenAI Endpoint URL <span className="text-rose-500">*</span>
                </label>
                <Input
                  type="text"
                  placeholder="https://your-resource-name.openai.azure.com/"
                  value={azureEndpoint}
                  onChange={(e) => setAzureEndpoint(e.target.value)}
                />
                <span className="text-[11px] text-ink-subtle mt-1 block">
                  Found under Keys and Endpoint in your Azure OpenAI resource.
                </span>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Azure API Key <span className="text-rose-500">*</span>
                </label>
                <Input
                  type="password"
                  placeholder="Paste Key 1 or Key 2"
                  value={azureApiKey}
                  onChange={(e) => setAzureApiKey(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-ink mb-1">
                    Deployment Name (Optional)
                  </label>
                  <Input
                    type="text"
                    placeholder="gpt-4o-mini"
                    value={azureDeploymentName}
                    onChange={(e) => setAzureDeploymentName(e.target.value)}
                  />
                  <span className="text-[11px] text-ink-subtle mt-1 block">
                    Defaults to model name if left blank.
                  </span>
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink mb-1">
                    API Version
                  </label>
                  <Input
                    type="text"
                    value={azureApiVersion}
                    onChange={(e) => setAzureApiVersion(e.target.value)}
                  />
                </div>
              </div>

              <div className="pt-2">
                <label className="block text-xs font-medium text-ink mb-1">
                  Primary Model Selection
                </label>
                <select
                  value={azureSelectedModel}
                  onChange={(e) => setAzureSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-md border border-surface-border bg-white text-ink focus:outline-none focus:ring-2 focus:ring-lime-500"
                >
                  {azureModels.length > 0 ? (
                    azureModels.map((m) => (
                      <option key={m.model_id} value={m.model_id}>
                        {m.display_name} ({m.role})
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="azure.gpt-4o-mini">GPT-4o Mini (Interviewer & Hints - Fast & Cheap)</option>
                      <option value="azure.gpt-4o">GPT-4o (Deep Evaluation & Rubric Grading)</option>
                      <option value="azure.phi-3.5-mini">Microsoft Phi-3.5 Mini (Lightweight)</option>
                    </>
                  )}
                </select>
              </div>
            </div>
          </Card>
        </div>
      ) : (
        <div className="space-y-6">
          {/* AWS Instructions */}
          <Card className="border-l-4 border-l-amber-500 space-y-3">
            <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 text-xs font-bold flex items-center justify-center">1</span>
              Quick AWS Bedrock Linking Guide (3 Minutes)
            </h3>
            <ol className="text-xs text-ink-muted space-y-1.5 list-decimal pl-5">
              <li>
                Open the <a href="https://console.aws.amazon.com/bedrock/" target="_blank" rel="noreferrer" className="text-amber-800 underline font-medium inline-flex items-center gap-0.5">AWS Bedrock Console <ExternalLink className="w-3 h-3" /></a> and ensure <strong>Model Access</strong> is granted for your chosen model.
              </li>
              <li>
                In the AWS IAM Console, create an IAM Policy using the generated least-privilege JSON below.
              </li>
              <li>
                Attach the policy to an IAM User and generate programmatic <strong>Access Keys</strong>.
              </li>
            </ol>
          </Card>

          {/* AWS Budget Warning Banner */}
          <div className="rounded-xl border border-rose-300 bg-rose-50/70 p-4 flex gap-3 items-start">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="text-xs text-rose-900 leading-relaxed">
              <strong className="font-semibold block text-rose-950 mb-0.5">
                AWS Credit Card Billing Warning:
              </strong>
              AWS Bedrock charges your personal credit card for token usage. Navigate to <strong>AWS Billing Console → Budgets</strong> and set an email alert (e.g. at $5.00) so you never get billed unexpectedly.
            </div>
          </div>

          {/* Least-Privilege IAM Policy Box */}
          <Card className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-ink">Least-Privilege AWS IAM Policy</h3>
                <p className="text-xs text-ink-muted">Attach this to your IAM User. Strictly allows only bedrock:InvokeModel.</p>
              </div>
              <Button size="sm" variant="outline" onClick={handleCopyPolicy} className="gap-1.5">
                {policyCopied ? <Check className="w-3.5 h-3.5 text-lime-600" /> : <Copy className="w-3.5 h-3.5" />}
                {policyCopied ? 'Copied' : 'Copy JSON'}
              </Button>
            </div>
            <pre className="p-3 bg-zinc-900 text-zinc-100 text-xs rounded-lg overflow-x-auto font-mono max-h-48 border border-zinc-800">
              {policyDoc || 'Generating policy...'}
            </pre>
          </Card>

          {/* AWS Form */}
          <Card className="space-y-4">
            <h3 className="text-base font-semibold text-ink">AWS IAM Credentials</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-ink mb-1">AWS Region</label>
                <select
                  value={bedrockRegion}
                  onChange={(e) => setBedrockRegion(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-md border border-surface-border bg-white text-ink focus:outline-none focus:ring-2 focus:ring-lime-500"
                >
                  <option value="us-east-1">us-east-1 (N. Virginia)</option>
                  <option value="us-west-2">us-west-2 (Oregon)</option>
                  <option value="ap-south-1">ap-south-1 (Mumbai)</option>
                  <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-ink mb-1">Preferred Model</label>
                <select
                  value={bedrockModel}
                  onChange={(e) => setBedrockModel(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-md border border-surface-border bg-white text-ink focus:outline-none focus:ring-2 focus:ring-lime-500"
                >
                  {bedrockModels.length > 0 ? (
                    bedrockModels.map((m) => (
                      <option key={m.model_id} value={m.model_id}>
                        {m.display_name} ({m.role})
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="qwen.qwen3-32b-v1:0">Qwen3 32B (Default)</option>
                      <option value="us.deepseek.r1-v1:0">DeepSeek R1 (Evaluations)</option>
                      <option value="qwen.qwen3-coder-30b-a3b-v1:0">Qwen3 Coder 30B</option>
                      <option value="amazon.nova-lite-v1:0">Amazon Nova Lite</option>
                    </>
                  )}
                </select>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  AWS Access Key ID <span className="text-rose-500">*</span>
                </label>
                <Input
                  type="text"
                  placeholder="AKIAIOSFODNN7EXAMPLE"
                  value={awsAccessKeyId}
                  onChange={(e) => setAwsAccessKeyId(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  AWS Secret Access Key <span className="text-rose-500">*</span>
                </label>
                <Input
                  type="password"
                  placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                  value={awsSecretAccessKey}
                  onChange={(e) => setAwsSecretAccessKey(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  AWS Session Token (Optional)
                </label>
                <Input
                  type="password"
                  placeholder="Optional temporary STS session token"
                  value={awsSessionToken}
                  onChange={(e) => setAwsSessionToken(e.target.value)}
                />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Test Feedback & Error Alerts */}
      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {testResult && (
        <div
          className={`p-3.5 rounded-lg text-xs flex items-start gap-2.5 border ${
            testResult.success
              ? 'bg-lime-50/80 border-lime-200 text-lime-900'
              : 'bg-rose-50/80 border-rose-200 text-rose-900'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2 className="w-4 h-4 text-lime-600 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <span className="font-semibold block">{testResult.success ? 'Connection Verified' : 'Connection Failed'}</span>
            <span className="text-xs opacity-90">{testResult.message}</span>
            {testResult.latency_ms && (
              <span className="block text-[11px] text-ink-subtle mt-0.5">Round-trip latency: {testResult.latency_ms} ms</span>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={handleTestConnection}
          disabled={isTesting}
          className="w-full sm:w-auto"
        >
          {isTesting ? 'Testing Connectivity...' : 'Test Connection'}
        </Button>

        <Button
          type="button"
          onClick={handleCompleteSetup}
          disabled={isSaving}
          className="w-full sm:w-auto bg-lime-600 hover:bg-lime-700 text-white gap-2"
        >
          {isSaving ? 'Encrypting & Saving...' : 'Save & Continue'}
          <ArrowRight className="w-4 h-4" />
        </Button>
      </div>

      <div className="text-center">
        <p className="text-xs text-ink-subtle flex items-center justify-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-zinc-400" />
          AES-256 encrypted at rest. Isolated per student tenant. Never logged or exposed.
        </p>
      </div>
    </div>
  );
};
