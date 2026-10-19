# Feature Map — Skill Issue

This document maps all high-level product features to their implementing services, API routes, database entities, and governing ADRs.

| Feature | Implementing Service | API Route | Frontend Component | Database Table | Governing ADR |
|---|---|---|---|---|---|
| **Authentication & User Management** | `svc:auth` | See API Routes | `fe:auth` | Tables | `—` |
| **BYOC & Model Configuration** | `svc:providers, svc:model_factory` | See API Routes | `fe:settings` | Tables | `—` |
| **Domain-Based Interview Setup** | `svc:resumes` | See API Routes | `—` | Tables | `—` |
| **JD-Based Interview Setup** | `svc:jds` | See API Routes | `—` | Tables | `—` |
| **Adaptive Interview Session** | `svc:interviews` | See API Routes | `fe:session` | Tables | `adr:0001` |
| **Candidate Self-Evaluation** | `svc:evaluations` | See API Routes | `—` | Tables | `—` |
| **AI Evidence-Based Evaluation** | `svc:evaluations` | See API Routes | `fe:evaluation` | Tables | `—` |
| **Planly Adaptive Improvement Engine** | `svc:plans` | See API Routes | `fe:planly` | Tables | `—` |
| **Secure Coding Sandbox** | `svc:coding` | See API Routes | `—` | Tables | `—` |
| **Progress Tracking & Reassessment** | `svc:analytics` | See API Routes | `fe:progress` | Tables | `—` |
