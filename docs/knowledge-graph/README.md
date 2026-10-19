# Codebase Knowledge Graph

This directory maintains the persistent, machine-readable knowledge graph for Skill Issue.

## Files
- [`graph.json`](graph.json): Authoritative Schema v1.0 machine-readable nodes and edges.
- [`graph.mmd`](graph.mmd): Mermaid visualization for human and agent review.
- [`feature-map.md`](feature-map.md): High-level feature-to-implementation cross-reference.
- [`dependency-map.md`](dependency-map.md): Architectural service-to-service dependency contracts.

## Regeneration
Whenever routes, services, tables, or ADRs are added or modified, execute:
```bash
python3 scripts/generate_knowledge_graph.py
```
