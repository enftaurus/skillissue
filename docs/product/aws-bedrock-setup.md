# Student Guide: Connecting Amazon Bedrock (BYOC)

Welcome to Skill Issue's Bring-Your-Own-Cloud (BYOC) setup. By using your own AWS credentials, you run AI models directly with Amazon Bedrock without middleman markups or subscription fees.

This guide takes about 5 minutes to complete. Follow each step carefully.

---

## Step 1 — Prepare Your AWS Account

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. If this is a new AWS account, verify that a valid payment method is configured.
3. **Safety First**: Never use your AWS Root user for daily tasks or API keys. Always operate as an IAM user.

---

## Step 2 — Select a Supported Region

Amazon Bedrock model availability and pricing vary by AWS region. Skill Issue currently recommends:

- **US East (N. Virginia) `us-east-1`** *(Recommended)*: Broadest model availability, lowest latency, and most competitive token pricing.
- **US West (Oregon) `us-west-2`**: High availability and excellent redundancy.
- **Europe (Frankfurt) `eu-central-1`**: Optimal for European privacy compliance.

> **Note:** Choose one region and keep it consistent across your Bedrock model access and Skill Issue settings.

---

## Step 3 — Enable Model Access in Bedrock

Before any API call will succeed, you must explicitly enable model access in the AWS Console:

1. In the AWS Console search bar, type **Amazon Bedrock** and open the service.
2. In the left navigation menu, scroll down and click **Model access**.
3. Click the orange **Modify model access** button (top right).
4. Select the models you want to use:
   - **Anthropic Claude 3.5 Sonnet / Haiku** (or Amazon Nova Pro / Lite / Micro)
   - **Meta Llama 3 / 3.1 70B & 8B**
   - **Mistral Large / Small**
5. Click **Next**, review the End User License Agreements (EULA), and click **Submit**.
6. Access is usually granted within 1–2 minutes (status turns green: *Access granted*).

---

## Step 4 — Create Least-Privilege IAM Credentials

Create a dedicated IAM user with only the exact permissions Skill Issue needs.

1. Navigate to the **IAM Console** (`Services` → `IAM` → `Users`).
2. Click **Create user**.
   - User name: `skill-issue-bedrock-runner`
   - Do **NOT** check "Provide user access to the AWS Management Console" (this is an API-only service user).
   - Click **Next**.
3. Select **Attach policies directly**, then click **Create policy** (opens a new tab).
4. Click the **JSON** tab and paste this exact least-privilege policy:

```json
{
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
}
```

5. Name the policy `SkillIssueBedrockAccess` and click **Create policy**.
6. Return to the user creation tab, search for `SkillIssueBedrockAccess`, check the box, and click **Next** → **Create user**.
7. Click on your newly created user (`skill-issue-bedrock-runner`), open the **Security credentials** tab.
8. Scroll to **Access keys** and click **Create access key**.
   - Select **Application running outside AWS** → click **Next** → click **Create access key**.
9. **Copy your Access Key ID and Secret Access Key now**. You will not be able to view the secret key again in AWS.

> **SECURITY INVARIANT**: Never share your Secret Access Key. Never paste it in chat, push it to GitHub, or embed it in code.

---

## Step 5 — Configure Skill Issue

1. Open Skill Issue and go to **Settings → AI Provider Settings**.
2. Select **Amazon Bedrock**.
3. Fill in:
   - **AWS Region**: e.g., `us-east-1`
   - **AWS Access Key ID**: e.g., `AKIA...`
   - **AWS Secret Access Key**: e.g., `wJalrXUtnFEMI...`
   - **Preferred Model**: e.g., `anthropic.claude-3-5-sonnet-20240620-v1:0` or `amazon.nova-pro-v1:0`
4. Click **Test & Save Configuration**.
5. Skill Issue will validate the credentials against AWS Bedrock live and store them encrypted using AES-256.

---

## Step 6 — Understand Costs & $20 Planning Budget

Skill Issue is engineered to be lightweight, respectful, and cost-effective.

1. **How Billing Works**: AWS charges for input tokens (prompts + conversation history) and output tokens (AI responses).
2. **Typical Costs**: A 15-minute mock interview generates roughly 6,000–12,000 tokens total. With models like Claude 3.5 Haiku or Amazon Nova Lite, a full interview costs approximately **\$0.01 to \$0.04**.
3. **The \$20 Planning Budget**: A \$20 initial credit gives you enough headroom for **500+ realistic practice sessions**.
4. **AWS Budget Alerts**: AWS Budget alerts send an email notification when thresholds are crossed, but **they do not automatically shut off your account**. You can set a \$10 or \$20 budget alert in AWS Cost Management.
5. **Official Pricing**: Consult the [AWS Bedrock Pricing Page](https://aws.amazon.com/bedrock/pricing/) for current regional rates.

---

## Step 7 — Revoking Credentials

You maintain 100% control over your credentials:

- **Inside Skill Issue**: Click **Delete Saved Credentials** in Provider Settings anytime. Your encrypted keys are permanently deleted from our database.
- **Inside AWS**: Go to IAM → Users → `skill-issue-bedrock-runner` → Security credentials → Deactivate or Delete the access key. Deletion takes effect instantly worldwide.
