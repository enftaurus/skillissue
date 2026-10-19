# Dependency Map — Skill Issue

## Service Dependency Matrix

The following matrix outlines runtime invocations between application modules:

- **InterviewService** → `ModelFactory`, `InterviewMessages`, `DatabaseSession`
- **EvaluationService** → `ModelFactory`, `RubricsCatalog`, `DatabaseSession`
- **PlanService** → `ModelFactory`, `EvaluationService`, `DatabaseSession`
- **CodingService** → `SandboxRunner`, `DatabaseSession`
- **ResumeService** → `ModelFactory`, `DatabaseSession`
- **JobDescriptionService** → `ModelFactory`, `DatabaseSession`
- **ModelFactory** → `AmazonBedrockProvider`, `MockProvider`
- **SandboxRunner** → Ephemeral Docker / Subprocess Worker
