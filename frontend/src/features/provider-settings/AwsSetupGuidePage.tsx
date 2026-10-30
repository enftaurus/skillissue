import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Check, Copy, ExternalLink, ArrowRight } from 'lucide-react';

export const AwsSetupGuidePage: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const policyJson = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SkillIssueBedrockInvocation",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    }
  ]
}`;

  const handleCopyPolicy = () => {
    navigator.clipboard.writeText(policyJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Badge variant="brand">5-Minute Walkthrough</Badge>
          <span className="text-xs text-ink-subtle">Updated for AWS Bedrock Console</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-ink mt-2">
          Connecting Amazon Bedrock (BYOC)
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Skill Issue operates directly against your AWS account. You pay AWS raw token prices without subscription fees or middleman markups.
        </p>
      </div>

      <div className="space-y-6">
        {/* Step 1 */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-ink flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 text-xs font-bold flex items-center justify-center">1</span>
              Prepare an AWS Account
            </h3>
            <a
              href="https://console.aws.amazon.com/"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
            >
              AWS Console <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <p className="text-sm text-ink-muted leading-relaxed">
            Log in to the AWS Console. Ensure your account has active billing configured. Never generate API keys using your AWS Root account; always create a dedicated IAM user as outlined below.
          </p>
        </Card>

        {/* Step 2 */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-ink flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 text-xs font-bold flex items-center justify-center">2</span>
              Select a Supported AWS Region
            </h3>
          </div>
          <p className="text-sm text-ink-muted leading-relaxed">
            Amazon Bedrock model availability varies by region. For the best latency and access to our recommended <strong>Qwen3 32B</strong> model, select one of:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-surface-warm rounded-md border border-surface-border">
              <span className="font-bold text-ink">US East (N. Virginia) `us-east-1`</span>
              <p className="text-ink-subtle mt-0.5">Broadest model access, standard pricing.</p>
            </div>
            <div className="p-3 bg-surface-warm rounded-md border border-surface-border">
              <span className="font-bold text-ink">Asia Pacific (Sydney) `ap-southeast-2`</span>
              <p className="text-ink-subtle mt-0.5">Reference region for Qwen3 32B pricing.</p>
            </div>
          </div>
        </Card>

        {/* Step 3 */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-ink flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 text-xs font-bold flex items-center justify-center">3</span>
              Enable Model Access in Bedrock Console
            </h3>
          </div>
          <ol className="list-decimal list-inside space-y-1.5 text-sm text-ink-muted">
            <li>In AWS search, type <strong>Amazon Bedrock</strong> and click the service.</li>
            <li>In the left sidebar, click <strong>Model access</strong>.</li>
            <li>Click the orange <strong>Modify model access</strong> button.</li>
            <li>Check the boxes for <strong>Qwen3 32B</strong>, <strong>Qwen3 Coder 30B</strong>, and <strong>Qwen3 Next 80B</strong>.</li>
            <li>Click <strong>Next</strong> and submit. Access is granted within 1–2 minutes.</li>
          </ol>
        </Card>

        {/* Step 4 */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-ink flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 text-xs font-bold flex items-center justify-center">4</span>
              Create Least-Privilege IAM Credentials
            </h3>
            <Button variant="outline" size="sm" onClick={handleCopyPolicy}>
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied Policy!' : 'Copy IAM Policy'}
            </Button>
          </div>
          <p className="text-sm text-ink-muted">
            In the <strong>IAM Console</strong> (`Users` → `Create user`), name the user <code className="bg-surface-subtle px-1.5 py-0.5 rounded text-xs font-mono">skill-issue-bedrock</code>. Attach only this exact least-privilege permission policy:
          </p>
          <pre className="bg-zinc-950 text-zinc-100 p-4 rounded-lg text-xs font-mono overflow-x-auto leading-relaxed">
            {policyJson}
          </pre>
          <p className="text-xs text-ink-subtle">
            Go to the user's `Security credentials` tab → click `Create access key` (Application outside AWS) → copy your <strong>Access Key ID</strong> and <strong>Secret Access Key</strong>.
          </p>
        </Card>

        {/* Step 5 */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-base text-ink flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80 text-xs font-bold flex items-center justify-center">5</span>
              Configure Skill Issue
            </h3>
            <Link to="/settings/provider">
              <Button variant="primary" size="sm">
                Open Provider Settings <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </Link>
          </div>
          <p className="text-sm text-ink-muted">
            Paste your credentials into Skill Issue settings. The server validates them live with Amazon Bedrock before encrypting them with AES-256. Secret keys are never logged, never returned in browser network calls, and masked across the UI.
          </p>
        </Card>

        {/* Step 6 & 7 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Card className="space-y-2">
            <h4 className="font-semibold text-sm text-ink">Understanding Costs & $20 Budget</h4>
            <p className="text-xs text-ink-muted leading-relaxed">
              AWS charges strictly by input/output tokens. At Qwen3 32B rates ($0.1545 / $0.618 per 1M), a 20-minute mock session costs roughly <strong>$0.003 to $0.006</strong>. A $20 student budget provides over 500 complete interview loops.
            </p>
          </Card>

          <Card className="space-y-2">
            <h4 className="font-semibold text-sm text-ink">Revoking Credentials</h4>
            <p className="text-xs text-ink-muted leading-relaxed">
              You maintain total sovereignty. You can click <strong>Purge Credentials</strong> in Provider Settings at any time, or deactivate/delete the access key inside AWS IAM to immediately cut off access globally.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
};
