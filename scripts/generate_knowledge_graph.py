#!/usr/bin/env python3
"""
Generate the machine-readable knowledge graph and documentation for Skill Issue.
Generates:
  - docs/knowledge-graph/graph.json (Typed nodes and edges, Schema v1.0)
  - docs/knowledge-graph/graph.mmd (Mermaid diagram)
  - docs/knowledge-graph/feature-map.md
  - docs/knowledge-graph/dependency-map.md
  - docs/knowledge-graph/README.md
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_KG = ROOT / "docs" / "knowledge-graph"

NODES = [
    # Product Features
    {"id": "feat:auth", "type": "ProductFeature", "name": "Authentication & User Management", "description": "Email/password auth, JWT sessions, user isolation, account deletion"},
    {"id": "feat:byoc", "type": "ProductFeature", "name": "BYOC & Model Configuration", "description": "Amazon Bedrock integration, credential encryption at rest, cost tracking"},
    {"id": "feat:interview_domain", "type": "ProductFeature", "name": "Domain-Based Interview Setup", "description": "Skill selection, optional resume parsing, customized interview scope"},
    {"id": "feat:interview_jd", "type": "ProductFeature", "name": "JD-Based Interview Setup", "description": "Job description text extraction, requirements mapping, focused interview scope"},
    {"id": "feat:interview_session", "type": "ProductFeature", "name": "Adaptive Interview Session", "description": "1-question-at-a-time, natural human tone, voice/text fallback, follow-ups"},
    {"id": "feat:self_eval", "type": "ProductFeature", "name": "Candidate Self-Evaluation", "description": "Pre-AI rubric dimension rating by the student"},
    {"id": "feat:ai_eval", "type": "ProductFeature", "name": "AI Evidence-Based Evaluation", "description": "Post-interview rubric evaluation with quote excerpts, strengths, gaps"},
    {"id": "feat:planly", "type": "ProductFeature", "name": "Planly Adaptive Improvement Engine", "description": "Dynamic multi-day task generation, learning resources, schedule adjustment"},
    {"id": "feat:coding_sandbox", "type": "ProductFeature", "name": "Secure Coding Sandbox", "description": "Isolated execution of Python, Java, and C++ code submissions"},
    {"id": "feat:progress_analytics", "type": "ProductFeature", "name": "Progress Tracking & Reassessment", "description": "Comparable rubric score trends and mastery indicators over time"},

    # ADRs
    {"id": "adr:0001", "type": "ADR", "path": "docs/decisions/0001-modular-monolith.md", "name": "Modular Monolith Architecture"},
    {"id": "adr:0002", "type": "ADR", "path": "docs/decisions/0002-provider-abstraction.md", "name": "Model Provider Abstraction & Factory"},
    {"id": "adr:0003", "type": "ADR", "path": "docs/decisions/0003-bedrock-byoc.md", "name": "BYOC with Amazon Bedrock"},
    {"id": "adr:0004", "type": "ADR", "path": "docs/decisions/0004-postgresql-docker.md", "name": "Containerized PostgreSQL with Docker Volume"},
    {"id": "adr:0005", "type": "ADR", "path": "docs/decisions/0005-credential-encryption.md", "name": "At-Rest Credential Encryption"},
    {"id": "adr:0006", "type": "ADR", "path": "docs/decisions/0006-interview-engine-and-rubrics.md", "name": "Unified Interview Engine & Post-Evaluation"},
    {"id": "adr:0007", "type": "ADR", "path": "docs/decisions/0007-coding-sandbox-architecture.md", "name": "Isolated Execution Sandbox"},
    {"id": "adr:0008", "type": "ADR", "path": "docs/decisions/0008-planly-adaptive-engine.md", "name": "Planly Adaptive Learning Engine"},

    # API Routes
    {"id": "route:auth", "type": "APIRoute", "path": "backend/app/api/v1/auth.py", "name": "/api/v1/auth/*"},
    {"id": "route:providers", "type": "APIRoute", "path": "backend/app/api/v1/providers.py", "name": "/api/v1/providers/*"},
    {"id": "route:interviews", "type": "APIRoute", "path": "backend/app/api/v1/interviews.py", "name": "/api/v1/interviews/*"},
    {"id": "route:evaluations", "type": "APIRoute", "path": "backend/app/api/v1/evaluations.py", "name": "/api/v1/evaluations/*"},
    {"id": "route:plans", "type": "APIRoute", "path": "backend/app/api/v1/plans.py", "name": "/api/v1/plans/*"},
    {"id": "route:resumes", "type": "APIRoute", "path": "backend/app/api/v1/resumes.py", "name": "/api/v1/resumes/*"},
    {"id": "route:job_descriptions", "type": "APIRoute", "path": "backend/app/api/v1/job_descriptions.py", "name": "/api/v1/job_descriptions/*"},
    {"id": "route:coding", "type": "APIRoute", "path": "backend/app/api/v1/coding.py", "name": "/api/v1/coding/*"},
    {"id": "route:analytics", "type": "APIRoute", "path": "backend/app/api/v1/analytics.py", "name": "/api/v1/analytics/*"},
    {"id": "route:health", "type": "APIRoute", "path": "backend/app/api/v1/health.py", "name": "/api/v1/health"},

    # Services
    {"id": "svc:auth", "type": "Service", "path": "backend/app/auth/service.py", "name": "AuthService"},
    {"id": "svc:providers", "type": "Service", "path": "backend/app/providers/service.py", "name": "ProviderConfigService"},
    {"id": "svc:model_factory", "type": "Service", "path": "backend/app/providers/factory.py", "name": "ModelFactory"},
    {"id": "svc:interviews", "type": "Service", "path": "backend/app/interviews/service.py", "name": "InterviewService"},
    {"id": "svc:evaluations", "type": "Service", "path": "backend/app/evaluations/service.py", "name": "EvaluationService"},
    {"id": "svc:plans", "type": "Service", "path": "backend/app/plans/service.py", "name": "PlanService"},
    {"id": "svc:resumes", "type": "Service", "path": "backend/app/resumes/service.py", "name": "ResumeService"},
    {"id": "svc:jds", "type": "Service", "path": "backend/app/job_descriptions/service.py", "name": "JobDescriptionService"},
    {"id": "svc:coding", "type": "Service", "path": "backend/app/coding/service.py", "name": "CodingService"},
    {"id": "svc:analytics", "type": "Service", "path": "backend/app/analytics/service.py", "name": "AnalyticsService"},

    # Database Tables
    {"id": "tbl:users", "type": "DatabaseTable", "name": "users"},
    {"id": "tbl:user_profiles", "type": "DatabaseTable", "name": "user_profiles"},
    {"id": "tbl:provider_configs", "type": "DatabaseTable", "name": "provider_configs"},
    {"id": "tbl:resumes", "type": "DatabaseTable", "name": "resumes"},
    {"id": "tbl:job_descriptions", "type": "DatabaseTable", "name": "job_descriptions"},
    {"id": "tbl:interviews", "type": "DatabaseTable", "name": "interviews"},
    {"id": "tbl:interview_messages", "type": "DatabaseTable", "name": "interview_messages"},
    {"id": "tbl:self_evaluations", "type": "DatabaseTable", "name": "self_evaluations"},
    {"id": "tbl:evaluations", "type": "DatabaseTable", "name": "evaluations"},
    {"id": "tbl:plans", "type": "DatabaseTable", "name": "plans"},
    {"id": "tbl:plan_tasks", "type": "DatabaseTable", "name": "plan_tasks"},
    {"id": "tbl:coding_submissions", "type": "DatabaseTable", "name": "coding_submissions"},

    # Model Providers
    {"id": "prov:bedrock", "type": "ModelProvider", "name": "AmazonBedrockProvider", "path": "backend/app/providers/bedrock.py"},
    {"id": "prov:mock", "type": "ModelProvider", "name": "MockProvider", "path": "backend/app/providers/mock_provider.py"},

    # Sandbox
    {"id": "sand:runner", "type": "Module", "name": "SandboxRunner", "path": "sandbox/runner.py"},

    # Frontend Features
    {"id": "fe:auth", "type": "FrontendFeature", "path": "frontend/src/features/auth", "name": "AuthUI"},
    {"id": "fe:settings", "type": "FrontendFeature", "path": "frontend/src/features/provider-settings", "name": "ProviderSettingsUI"},
    {"id": "fe:setup", "type": "FrontendFeature", "path": "frontend/src/features/interview-setup", "name": "InterviewSetupUI"},
    {"id": "fe:session", "type": "FrontendFeature", "path": "frontend/src/features/interview-session", "name": "InterviewSessionUI"},
    {"id": "fe:evaluation", "type": "FrontendFeature", "path": "frontend/src/features/evaluation", "name": "EvaluationUI"},
    {"id": "fe:planly", "type": "FrontendFeature", "path": "frontend/src/features/improvement-plan", "name": "PlanlyUI"},
    {"id": "fe:progress", "type": "FrontendFeature", "path": "frontend/src/features/progress", "name": "ProgressUI"}
]

EDGES = [
    # Feature implements
    {"source": "svc:auth", "target": "feat:auth", "type": "implements"},
    {"source": "fe:auth", "target": "feat:auth", "type": "implements"},
    {"source": "svc:providers", "target": "feat:byoc", "type": "implements"},
    {"source": "svc:model_factory", "target": "feat:byoc", "type": "implements"},
    {"source": "fe:settings", "target": "feat:byoc", "type": "implements"},
    {"source": "svc:interviews", "target": "feat:interview_session", "type": "implements"},
    {"source": "fe:session", "target": "feat:interview_session", "type": "implements"},
    {"source": "svc:resumes", "target": "feat:interview_domain", "type": "implements"},
    {"source": "svc:jds", "target": "feat:interview_jd", "type": "implements"},
    {"source": "svc:evaluations", "target": "feat:ai_eval", "type": "implements"},
    {"source": "svc:evaluations", "target": "feat:self_eval", "type": "implements"},
    {"source": "fe:evaluation", "target": "feat:ai_eval", "type": "implements"},
    {"source": "svc:plans", "target": "feat:planly", "type": "implements"},
    {"source": "fe:planly", "target": "feat:planly", "type": "implements"},
    {"source": "svc:coding", "target": "feat:coding_sandbox", "type": "implements"},
    {"source": "sand:runner", "target": "feat:coding_sandbox", "type": "implements"},
    {"source": "svc:analytics", "target": "feat:progress_analytics", "type": "implements"},
    {"source": "fe:progress", "target": "feat:progress_analytics", "type": "implements"},

    # ADR constraints
    {"source": "adr:0001", "target": "feat:interview_session", "type": "governs"},
    {"source": "adr:0002", "target": "svc:model_factory", "type": "governs"},
    {"source": "adr:0003", "target": "prov:bedrock", "type": "governs"},
    {"source": "adr:0004", "target": "tbl:users", "type": "governs"},
    {"source": "adr:0005", "target": "svc:providers", "type": "governs"},
    {"source": "adr:0006", "target": "svc:interviews", "type": "governs"},
    {"source": "adr:0006", "target": "svc:evaluations", "type": "governs"},
    {"source": "adr:0007", "target": "sand:runner", "type": "governs"},
    {"source": "adr:0008", "target": "svc:plans", "type": "governs"},

    # Route calls Service
    {"source": "route:auth", "target": "svc:auth", "type": "calls"},
    {"source": "route:providers", "target": "svc:providers", "type": "calls"},
    {"source": "route:interviews", "target": "svc:interviews", "type": "calls"},
    {"source": "route:evaluations", "target": "svc:evaluations", "type": "calls"},
    {"source": "route:plans", "target": "svc:plans", "type": "calls"},
    {"source": "route:resumes", "target": "svc:resumes", "type": "calls"},
    {"source": "route:job_descriptions", "target": "svc:jds", "type": "calls"},
    {"source": "route:coding", "target": "svc:coding", "type": "calls"},
    {"source": "route:analytics", "target": "svc:analytics", "type": "calls"},

    # Service calls Factory / Providers
    {"source": "svc:interviews", "target": "svc:model_factory", "type": "calls"},
    {"source": "svc:evaluations", "target": "svc:model_factory", "type": "calls"},
    {"source": "svc:resumes", "target": "svc:model_factory", "type": "calls"},
    {"source": "svc:jds", "target": "svc:model_factory", "type": "calls"},
    {"source": "svc:plans", "target": "svc:model_factory", "type": "calls"},
    {"source": "svc:model_factory", "target": "prov:bedrock", "type": "resolves"},
    {"source": "svc:model_factory", "target": "prov:mock", "type": "resolves"},
    {"source": "svc:coding", "target": "sand:runner", "type": "calls"},

    # Database Reads & Writes
    {"source": "svc:auth", "target": "tbl:users", "type": "writes"},
    {"source": "svc:auth", "target": "tbl:user_profiles", "type": "writes"},
    {"source": "svc:providers", "target": "tbl:provider_configs", "type": "writes"},
    {"source": "svc:resumes", "target": "tbl:resumes", "type": "writes"},
    {"source": "svc:jds", "target": "tbl:job_descriptions", "type": "writes"},
    {"source": "svc:interviews", "target": "tbl:interviews", "type": "writes"},
    {"source": "svc:interviews", "target": "tbl:interview_messages", "type": "writes"},
    {"source": "svc:evaluations", "target": "tbl:self_evaluations", "type": "writes"},
    {"source": "svc:evaluations", "target": "tbl:evaluations", "type": "writes"},
    {"source": "svc:plans", "target": "tbl:plans", "type": "writes"},
    {"source": "svc:plans", "target": "tbl:plan_tasks", "type": "writes"},
    {"source": "svc:coding", "target": "tbl:coding_submissions", "type": "writes"},
    {"source": "svc:analytics", "target": "tbl:evaluations", "type": "reads"},
    {"source": "svc:analytics", "target": "tbl:interviews", "type": "reads"}
]

def main():
    DOCS_KG.mkdir(parents=True, exist_ok=True)

    # 1. Write graph.json
    graph_data = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "version": "1.0.0",
        "project": "Skill Issue",
        "description": "Machine-readable knowledge graph linking features, routes, services, database tables, and ADRs",
        "nodes": NODES,
        "edges": EDGES
    }
    graph_json_path = DOCS_KG / "graph.json"
    with open(graph_json_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"Generated {graph_json_path}")

    # 2. Write graph.mmd
    mmd_lines = [
        "graph TD",
        "    classDef feature fill:#84CC16,stroke:#4D7C0F,color:#000000;",
        "    classDef service fill:#E0E7FF,stroke:#4338CA,color:#1E1B4B;",
        "    classDef route fill:#FEF3C7,stroke:#B45309,color:#78350F;",
        "    classDef db fill:#F3F4F6,stroke:#4B5563,color:#111827;",
        "    classDef adr fill:#FCE7F3,stroke:#BE185D,color:#831843;",
        ""
    ]
    for edge in EDGES:
        s = edge["source"].replace(":", "_")
        t = edge["target"].replace(":", "_")
        label = edge["type"]
        mmd_lines.append(f"    {s} -->|{label}| {t}")

    graph_mmd_path = DOCS_KG / "graph.mmd"
    with open(graph_mmd_path, "w", encoding="utf-8") as f:
        f.write("\n".join(mmd_lines) + "\n")
    print(f"Generated {graph_mmd_path}")

    # 3. Write feature-map.md
    feature_map_lines = [
        "# Feature Map — Skill Issue",
        "",
        "This document maps all high-level product features to their implementing services, API routes, database entities, and governing ADRs.",
        "",
        "| Feature | Implementing Service | API Route | Frontend Component | Database Table | Governing ADR |",
        "|---|---|---|---|---|---|"
    ]
    features = [n for n in NODES if n["type"] == "ProductFeature"]
    for feat in features:
        fid = feat["id"]
        services = [e["source"] for e in EDGES if e["target"] == fid and e["type"] == "implements" and e["source"].startswith("svc:")]
        fes = [e["source"] for e in EDGES if e["target"] == fid and e["type"] == "implements" and e["source"].startswith("fe:")]
        adrs = [e["source"] for e in EDGES if e["target"] == fid and e["type"] == "governs"]
        svc_str = ", ".join(services) if services else "—"
        fe_str = ", ".join(fes) if fes else "—"
        adr_str = ", ".join(adrs) if adrs else "—"
        feature_map_lines.append(f"| **{feat['name']}** | `{svc_str}` | See API Routes | `{fe_str}` | Tables | `{adr_str}` |")

    with open(DOCS_KG / "feature-map.md", "w", encoding="utf-8") as f:
        f.write("\n".join(feature_map_lines) + "\n")
    print(f"Generated {DOCS_KG / 'feature-map.md'}")

    # 4. Write dependency-map.md
    dep_lines = [
        "# Dependency Map — Skill Issue",
        "",
        "## Service Dependency Matrix",
        "",
        "The following matrix outlines runtime invocations between application modules:",
        "",
        "- **InterviewService** → `ModelFactory`, `InterviewMessages`, `DatabaseSession`",
        "- **EvaluationService** → `ModelFactory`, `RubricsCatalog`, `DatabaseSession`",
        "- **PlanService** → `ModelFactory`, `EvaluationService`, `DatabaseSession`",
        "- **CodingService** → `SandboxRunner`, `DatabaseSession`",
        "- **ResumeService** → `ModelFactory`, `DatabaseSession`",
        "- **JobDescriptionService** → `ModelFactory`, `DatabaseSession`",
        "- **ModelFactory** → `AmazonBedrockProvider`, `MockProvider`",
        "- **SandboxRunner** → Ephemeral Docker / Subprocess Worker"
    ]
    with open(DOCS_KG / "dependency-map.md", "w", encoding="utf-8") as f:
        f.write("\n".join(dep_lines) + "\n")
    print(f"Generated {DOCS_KG / 'dependency-map.md'}")

    # 5. Write README.md
    readme_lines = [
        "# Codebase Knowledge Graph",
        "",
        "This directory maintains the persistent, machine-readable knowledge graph for Skill Issue.",
        "",
        "## Files",
        "- [`graph.json`](graph.json): Authoritative Schema v1.0 machine-readable nodes and edges.",
        "- [`graph.mmd`](graph.mmd): Mermaid visualization for human and agent review.",
        "- [`feature-map.md`](feature-map.md): High-level feature-to-implementation cross-reference.",
        "- [`dependency-map.md`](dependency-map.md): Architectural service-to-service dependency contracts.",
        "",
        "## Regeneration",
        "Whenever routes, services, tables, or ADRs are added or modified, execute:",
        "```bash",
        "python3 scripts/generate_knowledge_graph.py",
        "```"
    ]
    with open(DOCS_KG / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines) + "\n")
    print(f"Generated {DOCS_KG / 'README.md'}")

if __name__ == "__main__":
    main()
