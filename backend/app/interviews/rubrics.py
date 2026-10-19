from typing import Dict, List
from pydantic import BaseModel

class RubricDimension(BaseModel):
    id: str
    name: str
    description: str
    max_score: int = 5
    scoring_criteria: Dict[int, str]

RUBRICS_CATALOG: Dict[str, List[RubricDimension]] = {
    "technical": [
        RubricDimension(
            id="technical_depth",
            name="Technical Depth & Accuracy",
            description="Correctness of technical assertions, precision with system internals, and avoidance of superficial buzzwords.",
            scoring_criteria={
                1: "Incorrect, confusing, or bluffing about fundamental concepts.",
                2: "Superficial understanding; relies on buzzwords without explaining mechanisms.",
                3: "Accurate at high level, but struggles when probed on internal mechanics or memory/concurrency trade-offs.",
                4: "Clear and mechanically accurate with concrete examples.",
                5: "Mastery: cites exact latency numbers, kernel/runtime trade-offs, and failure modes seamlessly."
            }
        ),
        RubricDimension(
            id="system_design_tradeoffs",
            name="System Design & Trade-offs",
            description="Ability to balance consistency vs availability, latency vs cost, and evaluate architectural alternatives.",
            scoring_criteria={
                1: "Single-point-of-failure architectures with no consideration of scale or failure.",
                2: "Aware of trade-offs in theory, but selects inappropriate tools for the problem.",
                3: "Recognizes major trade-offs (e.g. SQL vs NoSQL, sync vs async) with adequate rationale.",
                4: "Methodically analyzes bottlenecks, partition strategies, and failure tolerance.",
                5: "Principled trade-off evaluation under concrete throughput and budget constraints."
            }
        ),
        RubricDimension(
            id="communication_clarity",
            name="Communication & Precision",
            description="Conciseness, structure, and ability to explain complex mechanisms directly without conversational filler.",
            scoring_criteria={
                1: "Rambling, disorganized, or defensive when challenged.",
                2: "Unstructured explanation requiring multiple interviewer clarifications.",
                3: "Clear and understandable, with occasional minor tangents.",
                4: "Crisp, logical structure (context, problem, approach, result).",
                5: "Executive-level technical precision: efficient, direct, and answers the exact question asked."
            }
        ),
        RubricDimension(
            id="problem_solving_rigor",
            name="Diagnostic & Debugging Rigor",
            description="Systematic troubleshooting approach, hypothesis generation, and isolation of root causes.",
            scoring_criteria={
                1: "Guesses randomly at solutions without systematic diagnosis.",
                2: "Relies on trial-and-error without examining logs or telemetry.",
                3: "Follows standard debugging steps (reproduce, isolate, fix).",
                4: "Methodical hypothesis testing using metrics, flame graphs, and query analysis.",
                5: "Senior debugging instinct: identifies subtle race conditions, memory leaks, or network splits."
            }
        )
    ],
    "behavioral": [
        RubricDimension(
            id="situation_clarity",
            name="Context & Problem Framing (STAR)",
            description="Ability to set up the problem, stakes, and constraints without unnecessary backstory.",
            scoring_criteria={
                1: "Vague, confusing backstory with unclear stakes.",
                2: "Too much irrelevant narrative; hard to parse the core problem.",
                3: "Adequately frames the situation, stakes, and team context.",
                4: "Sharp, concise context highlighting technical/business constraints.",
                5: "Masterful framing: immediately conveys urgency, difficulty, and complexity."
            }
        ),
        RubricDimension(
            id="action_ownership",
            name="Personal Agency & Ownership",
            description="Distinguishes 'what I did' from 'what the team did'; takes accountability for outcomes.",
            scoring_criteria={
                1: "Uses passive 'we' throughout; unclear what the candidate personally contributed.",
                2: "Waited for instructions; limited personal initiative.",
                3: "Clearly articulates personal actions and contributions.",
                4: "Proactive leadership and ownership beyond formal job boundaries.",
                5: "Decisive personal accountability during crisis; took ownership of mistakes and pivoted."
            }
        ),
        RubricDimension(
            id="quantified_impact",
            name="Quantifiable Impact & Results",
            description="Measures success with real business/engineering metrics rather than emotional impressions.",
            scoring_criteria={
                1: "No metrics or claims outcome was 'successful' with no evidence.",
                2: "Vague outcome ('everyone was happy', 'it felt faster').",
                3: "Cites qualitative success with basic timeline or delivery metrics.",
                4: "Cites clear quantitative metrics (e.g. -40% deploy time, +25% conversion).",
                5: "Rigorous data-backed impact linked to team velocity and operational health."
            }
        ),
        RubricDimension(
            id="conflict_resolution",
            name="Constructive Collaboration & Disagreement",
            description="How disagreements are handled: using data, empathy, and professional integrity.",
            scoring_criteria={
                1: "Avoids conflict or acts combative/defensive when challenged.",
                2: "Concedes without rationale or forces decisions without consensus.",
                3: "Engages in healthy discussion and compromise.",
                4: "Uses prototypes and benchmarks to de-escalate subjective technical debates.",
                5: "Unites divergent stakeholders around shared engineering principles and data."
            }
        )
    ],
    "dsa": [
        RubricDimension(
            id="algorithm_correctness",
            name="Algorithmic Correctness & Logic",
            description="Soundness of data structure selection and code logic.",
            scoring_criteria={
                1: "Incorrect approach that fails basic logic.",
                2: "Brute force solution that fails large scale or timeout constraints.",
                3: "Correct approach with minor edge case oversights.",
                4: "Optimal data structure selection with clean, bug-free implementation.",
                5: "Flawless, optimal solution with consideration of hardware cache locality."
            }
        ),
        RubricDimension(
            id="time_complexity_analysis",
            name="Time Complexity Mastery",
            description="Accurate derivation of Best, Average, and Worst case Big-O time complexity.",
            scoring_criteria={
                1: "Unable to determine Big-O time complexity.",
                2: "Incorrect Big-O derivation or confuses auxiliary loops.",
                3: "Correct average case Big-O complexity.",
                4: "Accurately identifies worst-case degenerate scenarios and recurrence relations.",
                5: "Precise mathematical justification of time complexity under all input distributions."
            }
        ),
        RubricDimension(
            id="space_complexity_analysis",
            name="Space Complexity & Memory Allocation",
            description="Derivation of auxiliary space, call stack overhead, and in-place mutations.",
            scoring_criteria={
                1: "Ignores memory consumption or recursive call stack space.",
                2: "Confuses input size with auxiliary space.",
                3: "Correctly accounts for auxiliary arrays or hash tables.",
                4: "Identifies recursion stack depth and memory reallocation costs.",
                5: "Optimizes memory to O(1) auxiliary space where feasible."
            }
        ),
        RubricDimension(
            id="edge_case_handling",
            name="Edge Cases & Defensive Rigor",
            description="Proactive identification of empty inputs, single elements, overflow, and boundary conditions.",
            scoring_criteria={
                1: "Assumes happy-path inputs; crashes on null or empty arrays.",
                2: "Catches edge cases only when prompted by interviewer.",
                3: "Tests standard boundaries (empty input, duplicates, zero).",
                4: "Proactively identifies integer overflow, parity, and extreme bounds.",
                5: "Exhaustive edge-case validation before writing code."
            }
        )
    ],
    "managerial": [
        RubricDimension(
            id="architectural_tradeoffs",
            name="System Strategy & Architecture",
            description="Long-term technical roadmap, microservices vs monolith decisions, and platform scalability.",
            scoring_criteria={
                1: "Chases trendy tech stacks with no regard to maintenance cost.",
                2: "Struggles to articulate architectural vision or operational overhead.",
                3: "Balances feature velocity with architecture stability adequately.",
                4: "Articulates clear evolutionary architecture patterns.",
                5: "Distinguished architecture leadership: optimizes for cognitive load and system invariants."
            }
        ),
        RubricDimension(
            id="delivery_vs_debt",
            name="Technical Debt vs Delivery Velocity",
            description="Pragmatic prioritization of tech debt, refactoring budgets, and sprint commitments.",
            scoring_criteria={
                1: "Ignores tech debt until systems collapse, or insists on perfection halting all releases.",
                2: "Unbalanced prioritization causing team friction.",
                3: "Allocates explicit time for debt repayment.",
                4: "Treats technical debt quantitatively through SLA and defect-rate impact.",
                5: "Institutes automated guardrails preventing debt accumulation while maintaining velocity."
            }
        ),
        RubricDimension(
            id="cross_functional_collaboration",
            name="Cross-Functional Stakeholder Alignment",
            description="Translating technical complexity to Product, Design, and Executive leadership.",
            scoring_criteria={
                1: "Siloed communication; dismisses non-engineering concerns.",
                2: "Over-indexes on engineering jargon with business partners.",
                3: "Communicates project risks and timelines clearly.",
                4: "Aligns engineering decisions directly with business metrics.",
                5: "Trusted executive partner capable of negotiating scope without sacrificing architecture."
            }
        ),
        RubricDimension(
            id="team_mentorship",
            name="Engineering Culture & Mentorship",
            description="Leveling up junior/mid engineers, code review standards, and blameless postmortems.",
            scoring_criteria={
                1: "Does not invest in peers; dismissive during code reviews.",
                2: "Basic code reviews with little architectural teaching.",
                3: "Regularly assists teammates and participates in onboarding.",
                4: "Drives blameless postmortems and architectural design reviews.",
                5: "Force multiplier: creates an environment of engineering excellence and rapid growth."
            }
        )
    ]
}

def get_rubric_for_category(category: str) -> List[RubricDimension]:
    return RUBRICS_CATALOG.get(category.lower(), RUBRICS_CATALOG["technical"])
