"""company_registry.py — Registry of 50+ Top Tech Companies, Dynamic GitHub Fetcher, and Placement Simulations

Curated from real-world candidate interview debriefs gathered from community platforms (LeetCode Discuss, Reddit, Glassdoor).
Enforces Day-1 Unlock: Exactly 2–3 problems unlocked on Day 1, remaining unlocked progressively as problems are solved.
"""

from typing import Any, Dict, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

# Memory cache for raw github fetch
_GITHUB_CACHE: Dict[str, List[Dict[str, Any]]] = {}

COMPANIES_50: List[Dict[str, Any]] = [
    # GOLD TIER (12 companies)
    {
        "name": "Google",
        "slug": "google",
        "tier": "gold",
        "role_title": "Software Development Engineer (L3/L4)",
        "logo_icon": "Search",
        "description": "Google evaluates algorithmic elegance, time/space optimality, and Googleyness. Heavy emphasis on dynamic programming, trees, and graphs.",
        "community_tips": [
            "Expect zero sycophancy: Google interviewers test boundary conditions like negative weights and integer overflows.",
            "Always state big-O time and space complexity BEFORE writing code.",
            "In behavioral rounds, demonstrate bias to action, psychological safety, and disagree-and-commit."
        ],
        "problems": [
            {"title": "Longest Increasing Path in a Matrix", "slug": "longest-increasing-path-in-a-matrix", "difficulty": "HARD", "frequency": 100, "topics": ["DFS", "DP", "Graph", "Memoization"], "order": 1, "is_unlocked": True},
            {"title": "Word Ladder II", "slug": "word-ladder-ii", "difficulty": "HARD", "frequency": 96, "topics": ["BFS", "Backtracking", "Graph"], "order": 2, "is_unlocked": True},
            {"title": "Find Median from Data Stream", "slug": "find-median-from-data-stream", "difficulty": "HARD", "frequency": 94, "topics": ["Heap", "Two Pointers", "Design"], "order": 3, "is_unlocked": True},
            {"title": "Serialize and Deserialize Binary Tree", "slug": "serialize-and-deserialize-binary-tree", "difficulty": "HARD", "frequency": 91, "topics": ["Tree", "Design", "BFS"], "order": 4, "is_unlocked": False},
            {"title": "Split Array Largest Sum", "slug": "split-array-largest-sum", "difficulty": "HARD", "frequency": 88, "topics": ["Binary Search", "DP", "Greedy"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Uber",
        "slug": "uber",
        "tier": "gold",
        "role_title": "SDE-1 Backend & Systems Engineer",
        "logo_icon": "Car",
        "description": "High-throughput dispatching, geospatial routing, and concurrency primitives.",
        "community_tips": [
            "Bar-raisers heavily penalize global state and hand-waving thread safety.",
            "Expect 1 deep Graph/Topological Sort question and 1 Rate Limiter / Cache design question.",
            "Be prepared to explain how your algorithm scales to 500,000 active concurrent drivers."
        ],
        "problems": [
            {"title": "Escape the Spreading Fire", "slug": "escape-the-spreading-fire", "difficulty": "HARD", "frequency": 100, "topics": ["Array", "BFS", "Matrix", "Binary Search"], "order": 1, "is_unlocked": True},
            {"title": "Alien Dictionary", "slug": "alien-dictionary", "difficulty": "HARD", "frequency": 98, "topics": ["Graph", "Topological Sort", "DFS"], "order": 2, "is_unlocked": True},
            {"title": "Number of Islands II", "slug": "number-of-islands-ii", "difficulty": "HARD", "frequency": 95, "topics": ["Union Find", "Graph", "Matrix"], "order": 3, "is_unlocked": True},
            {"title": "Design Hit Counter", "slug": "design-hit-counter", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Design", "Queue", "Concurrency"], "order": 4, "is_unlocked": False},
            {"title": "Sliding Window Maximum", "slug": "sliding-window-maximum", "difficulty": "HARD", "frequency": 89, "topics": ["Queue", "Sliding Window", "Monotonic Queue"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "OpenAI",
        "slug": "openai",
        "tier": "gold",
        "role_title": "AI Systems & Infrastructure Engineer",
        "logo_icon": "Sparkles",
        "description": "Extreme scale LLM inference serving, GPU memory optimization, and distributed batching.",
        "community_tips": [
            "Heavy questioning on 'Why OpenAI?' and your concrete view on AGI safety vs shipping speed.",
            "Coding screen tests zero-copy memory pipelines, token streaming, and distributed queues.",
            "Interviewers will challenge you on handling tail latency during token generation."
        ],
        "problems": [
            {"title": "LRU Cache with TTL and Memory Budget", "slug": "lru-cache-with-ttl", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Hash Map", "Linked List", "Design"], "order": 1, "is_unlocked": True},
            {"title": "Maximum Frequency Stack", "slug": "maximum-frequency-stack", "difficulty": "HARD", "frequency": 97, "topics": ["Stack", "Hash Map", "Design"], "order": 2, "is_unlocked": True},
            {"title": "Stream of Characters (Trie)", "slug": "stream-of-characters", "difficulty": "HARD", "frequency": 93, "topics": ["Trie", "Stream", "Design"], "order": 3, "is_unlocked": True},
            {"title": "Design In-Memory File System", "slug": "design-in-memory-file-system", "difficulty": "HARD", "frequency": 90, "topics": ["Trie", "Design", "String"], "order": 4, "is_unlocked": False},
            {"title": "Shortest Path in a Grid with Obstacles Elimination", "slug": "shortest-path-obstacles", "difficulty": "HARD", "frequency": 88, "topics": ["BFS", "Matrix"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Meta",
        "slug": "meta",
        "tier": "gold",
        "role_title": "Software Engineer (E3/E4)",
        "logo_icon": "Globe",
        "description": "Rapid problem solving with two medium/hard questions in 45 minutes with zero compilation bugs.",
        "community_tips": [
            "Speed is vital: Meta expects you to finish 2 questions in 45 minutes with optimal time complexity.",
            "Write bug-free code on the first pass; do dry runs with edge cases before saying you're done.",
            "Top patterns: Binary Trees, Two Pointers, and Binary Search variations."
        ],
        "problems": [
            {"title": "Buildings With an Ocean View", "slug": "buildings-with-an-ocean-view", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Array", "Stack", "Monotonic Stack"], "order": 1, "is_unlocked": True},
            {"title": "Lowest Common Ancestor of a Binary Tree III", "slug": "lowest-common-ancestor-iii", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Tree", "Two Pointers", "Hash Table"], "order": 2, "is_unlocked": True},
            {"title": "Kth Largest Element in an Array", "slug": "kth-largest-element-in-an-array", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Quickselect", "Heap"], "order": 3, "is_unlocked": True},
            {"title": "Basic Calculator II", "slug": "basic-calculator-ii", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Math", "String", "Stack"], "order": 4, "is_unlocked": False},
            {"title": "Dot Product of Two Sparse Vectors", "slug": "dot-product-two-sparse-vectors", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Array", "Two Pointers", "Design"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Apple",
        "slug": "apple",
        "tier": "gold",
        "role_title": "Software Systems Engineer",
        "logo_icon": "Apple",
        "description": "Low-level system efficiency, hardware-software boundary, and clean memory semantics.",
        "community_tips": [
            "Apple interviewers test cache locality, memory footprint, and operating system basics.",
            "Strong focus on strings, bit manipulation, and linked lists.",
            "Demonstrate high attention to detail and user privacy architecture."
        ],
        "problems": [
            {"title": "Reverse Nodes in k-Group", "slug": "reverse-nodes-in-k-group", "difficulty": "HARD", "frequency": 98, "topics": ["Linked List", "Recursion"], "order": 1, "is_unlocked": True},
            {"title": "Trapping Rain Water", "slug": "trapping-rain-water", "difficulty": "HARD", "frequency": 95, "topics": ["Two Pointers", "Stack", "DP"], "order": 2, "is_unlocked": True},
            {"title": "Merge Intervals", "slug": "merge-intervals", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Array", "Sorting"], "order": 3, "is_unlocked": True},
            {"title": "Spiral Matrix", "slug": "spiral-matrix", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Array", "Matrix", "Simulation"], "order": 4, "is_unlocked": False},
            {"title": "Course Schedule II", "slug": "course-schedule-ii", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Graph", "Topological Sort", "BFS"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Netflix",
        "slug": "netflix",
        "tier": "gold",
        "role_title": "Senior Platform Engineer",
        "logo_icon": "Tv",
        "description": "High-concurrency streaming, chaos engineering, and extreme autonomy culture.",
        "community_tips": [
            "Netflix values 'Context, Not Control'—explain how you make technical decisions without supervision.",
            "Heavy emphasis on distributed caching, circuit breakers, and async RPC.",
            "Algorithms test streaming pipelines, sliding windows, and greedy scheduling."
        ],
        "problems": [
            {"title": "Design Video Upload Resumable Stream", "slug": "design-resumable-stream", "difficulty": "HARD", "frequency": 96, "topics": ["Design", "Sliding Window", "Stream"], "order": 1, "is_unlocked": True},
            {"title": "Task Scheduler", "slug": "task-scheduler", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Greedy", "Heap", "Hash Map"], "order": 2, "is_unlocked": True},
            {"title": "Median of Two Sorted Arrays", "slug": "median-two-sorted-arrays", "difficulty": "HARD", "frequency": 92, "topics": ["Binary Search", "Divide and Conquer"], "order": 3, "is_unlocked": True},
            {"title": "Group Anagrams", "slug": "group-anagrams", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Hash Map", "String", "Sorting"], "order": 4, "is_unlocked": False},
            {"title": "Word Search II", "slug": "word-search-ii", "difficulty": "HARD", "frequency": 85, "topics": ["Trie", "Backtracking", "Matrix"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Stripe",
        "slug": "stripe",
        "tier": "gold",
        "role_title": "Software Engineer (Payments Core)",
        "logo_icon": "CreditCard",
        "description": "Idempotent payment ledgers, distributed transactions, and practical production debugging.",
        "community_tips": [
            "Stripe does not use whiteboard puzzles: you will write real code with unit tests on your laptop.",
            "Expect questions on building an in-memory ledger with idempotent transaction replay.",
            "Edge cases: negative amounts, currency conversion rounding, and network dropouts."
        ],
        "problems": [
            {"title": "Implement Idempotent Payment Ledger", "slug": "implement-idempotent-ledger", "difficulty": "HARD", "frequency": 100, "topics": ["Design", "Hash Map", "Idempotency"], "order": 1, "is_unlocked": True},
            {"title": "Parse HTTP Accept-Language Header", "slug": "parse-accept-language", "difficulty": "MEDIUM", "frequency": 98, "topics": ["String", "Sorting", "Parser"], "order": 2, "is_unlocked": True},
            {"title": "Find Server Load Balancer Minimum Capacity", "slug": "server-load-balancer", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Two Pointers", "Binary Search"], "order": 3, "is_unlocked": True},
            {"title": "Design Rate Limiter with Sliding Log", "slug": "design-rate-limiter-sliding-log", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Design", "Sliding Window", "Queue"], "order": 4, "is_unlocked": False},
            {"title": "Valid Number", "slug": "valid-number", "difficulty": "HARD", "frequency": 87, "topics": ["String", "FSM", "Parser"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Palantir",
        "slug": "palantir",
        "tier": "gold",
        "role_title": "Forward Deployed Software Engineer (FDSE)",
        "logo_icon": "Shield",
        "description": "Complex graph algorithms, geospatial data, and ambiguous client-driven system problems.",
        "community_tips": [
            "Interviews test deep recursion, graph cycle detection, and large data structures.",
            "Explain how you translate ambiguous human requests into clean technical specifications.",
            "Expect a 60-minute decomposition round where you design an intelligence data pipeline."
        ],
        "problems": [
            {"title": "Word Ladder", "slug": "word-ladder", "difficulty": "HARD", "frequency": 98, "topics": ["BFS", "Graph", "Hash Table"], "order": 1, "is_unlocked": True},
            {"title": "Critical Connections in a Network", "slug": "critical-connections-network", "difficulty": "HARD", "frequency": 95, "topics": ["Graph", "Tarjan", "DFS"], "order": 2, "is_unlocked": True},
            {"title": "Design Search Autocomplete System", "slug": "design-search-autocomplete", "difficulty": "HARD", "frequency": 92, "topics": ["Trie", "Design", "Heap"], "order": 3, "is_unlocked": True},
            {"title": "Path with Maximum Gold", "slug": "path-with-maximum-gold", "difficulty": "MEDIUM", "frequency": 88, "topics": ["DFS", "Backtracking", "Matrix"], "order": 4, "is_unlocked": False},
            {"title": "Pacific Atlantic Water Flow", "slug": "pacific-atlantic-water-flow", "difficulty": "MEDIUM", "frequency": 85, "topics": ["BFS", "DFS", "Matrix"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "ByteDance",
        "slug": "bytedance",
        "tier": "gold",
        "role_title": "Backend Systems Engineer",
        "logo_icon": "Video",
        "description": "High-concurrency video feed ranking, Redis caching, and rigorous fast algorithm solving.",
        "community_tips": [
            "ByteDance technical screens are fast and intense: 3 coding problems in 60 minutes is standard.",
            "Expect deep questions on MySQL indexing, Redis cluster sharding, and Goroutine concurrency.",
            "Top topics: Dynamic Programming, Sliding Window, and Tree traversal."
        ],
        "problems": [
            {"title": "Longest Substring Without Repeating Characters", "slug": "longest-substring-without-repeating", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Sliding Window", "Hash Map"], "order": 1, "is_unlocked": True},
            {"title": "Binary Tree Maximum Path Sum", "slug": "binary-tree-maximum-path-sum", "difficulty": "HARD", "frequency": 96, "topics": ["Tree", "DFS", "DP"], "order": 2, "is_unlocked": True},
            {"title": "Search in Rotated Sorted Array", "slug": "search-rotated-sorted-array", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Binary Search", "Array"], "order": 3, "is_unlocked": True},
            {"title": "Edit Distance", "slug": "edit-distance", "difficulty": "HARD", "frequency": 90, "topics": ["String", "DP"], "order": 4, "is_unlocked": False},
            {"title": "Reorder List", "slug": "reorder-list", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Linked List", "Two Pointers"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Databricks",
        "slug": "databricks",
        "tier": "gold",
        "role_title": "Data Systems Engineer",
        "logo_icon": "Layers",
        "description": "Distributed query engines, Spark internals, and lock-free concurrent data structures.",
        "community_tips": [
            "Expect questions on concurrency, atomic operations, and memory-mapped file systems.",
            "Write production-grade code with error propagation and resource cleanup.",
            "Be prepared to optimize algorithms from O(N^2) to O(N log N) with custom comparators."
        ],
        "problems": [
            {"title": "Snapshot Array", "slug": "snapshot-array", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Array", "Hash Table", "Binary Search", "Design"], "order": 1, "is_unlocked": True},
            {"title": "Insert Delete GetRandom O(1) - Duplicates allowed", "slug": "insert-delete-getrandom-duplicates", "difficulty": "HARD", "frequency": 95, "topics": ["Array", "Hash Table", "Design"], "order": 2, "is_unlocked": True},
            {"title": "Range Sum Query 2D - Mutable", "slug": "range-sum-query-2d-mutable", "difficulty": "HARD", "frequency": 92, "topics": ["Segment Tree", "Binary Indexed Tree"], "order": 3, "is_unlocked": True},
            {"title": "LFU Cache", "slug": "lfu-cache", "difficulty": "HARD", "frequency": 89, "topics": ["Hash Map", "Linked List", "Design"], "order": 4, "is_unlocked": False},
            {"title": "Minimum Window Substring", "slug": "minimum-window-substring", "difficulty": "HARD", "frequency": 86, "topics": ["Hash Map", "Sliding Window", "String"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Snowflake",
        "slug": "snowflake",
        "tier": "gold",
        "role_title": "Core Database Kernel Engineer",
        "logo_icon": "Database",
        "description": "Cloud data warehousing, columnar storage execution, and vector optimization.",
        "community_tips": [
            "Snowflake focuses deeply on database primitives: B+ Trees, Columnar scans, and buffer pools.",
            "Zero tolerance for memory leaks in C++ and Java systems.",
            "Heavy emphasis on sorting, interval merging, and two-pointer stream joins."
        ],
        "problems": [
            {"title": "Merge k Sorted Lists", "slug": "merge-k-sorted-lists", "difficulty": "HARD", "frequency": 98, "topics": ["Linked List", "Divide and Conquer", "Heap"], "order": 1, "is_unlocked": True},
            {"title": "Count of Smaller Numbers After Self", "slug": "count-of-smaller-numbers", "difficulty": "HARD", "frequency": 94, "topics": ["Binary Indexed Tree", "Segment Tree", "Divide and Conquer"], "order": 2, "is_unlocked": True},
            {"title": "Range Module", "slug": "range-module", "difficulty": "HARD", "frequency": 91, "topics": ["Design", "Segment Tree", "Interval"], "order": 3, "is_unlocked": True},
            {"title": "Continuous Subarray Sum", "slug": "continuous-subarray-sum", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Array", "Hash Table", "Math", "Prefix Sum"], "order": 4, "is_unlocked": False},
            {"title": "Longest Consecutive Sequence", "slug": "longest-consecutive-sequence", "difficulty": "MEDIUM", "frequency": 84, "topics": ["Array", "Hash Table", "Union Find"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Anthropic",
        "slug": "anthropic",
        "tier": "gold",
        "role_title": "AI Infrastructure & Alignment Engineer",
        "logo_icon": "Cpu",
        "description": "Constitutional AI, massive parameter model training infrastructure, and GPU orchestration.",
        "community_tips": [
            "Interviewers probe your understanding of model evaluation harness design and RLHF mechanics.",
            "Expect practical system coding: async event pipelines, backpressure, and fault tolerance.",
            "Discuss trade-offs between evaluation precision and compute budget clearly."
        ],
        "problems": [
            {"title": "Design High-Throughput Batch Inference Pipeline", "slug": "design-batch-inference", "difficulty": "HARD", "frequency": 97, "topics": ["Queue", "Design", "Concurrency"], "order": 1, "is_unlocked": True},
            {"title": "Evaluate Reverse Polish Notation with Variables", "slug": "eval-rpn-variables", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Stack", "Math", "Parser"], "order": 2, "is_unlocked": True},
            {"title": "Decode String", "slug": "decode-string", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Stack", "Recursion", "String"], "order": 3, "is_unlocked": True},
            {"title": "Word Break II", "slug": "word-break-ii", "difficulty": "HARD", "frequency": 88, "topics": ["DP", "Trie", "Backtracking"], "order": 4, "is_unlocked": False},
            {"title": "All O(1) Data Structure", "slug": "all-o1-data-structure", "difficulty": "HARD", "frequency": 85, "topics": ["Hash Map", "Doubly-Linked List", "Design"], "order": 5, "is_unlocked": False},
        ]
    },

    # SILVER TIER (24 companies)
    {
        "name": "Amazon",
        "slug": "amazon",
        "tier": "silver",
        "role_title": "Software Development Engineer (SDE-1/2)",
        "logo_icon": "Package",
        "description": "Customer obsession, high-scale e-commerce transactions, and Amazon 16 Leadership Principles.",
        "community_tips": [
            "50% of your interview score depends on LP (Leadership Principles) stories using the STAR method.",
            "Expect Tree and Graph BFS/DFS questions, Two Pointers, and BFS for shortest distance.",
            "Never compromise on edge cases or input validation."
        ],
        "problems": [
            {"title": "Number of Islands", "slug": "number-of-islands", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Array", "BFS", "DFS", "Union Find"], "order": 1, "is_unlocked": True},
            {"title": "Rotting Oranges", "slug": "rotting-oranges", "difficulty": "MEDIUM", "frequency": 98, "topics": ["BFS", "Matrix"], "order": 2, "is_unlocked": True},
            {"title": "Reorganize String", "slug": "reorganize-string", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Heap", "Greedy", "String"], "order": 3, "is_unlocked": True},
            {"title": "Word Break", "slug": "word-break", "difficulty": "MEDIUM", "frequency": 91, "topics": ["DP", "Trie", "Hash Table"], "order": 4, "is_unlocked": False},
            {"title": "Analyze User Website Visit Pattern", "slug": "user-website-visit-pattern", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Array", "Hash Table", "Sorting"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Microsoft",
        "slug": "microsoft",
        "tier": "silver",
        "role_title": "Software Engineer (L59/L60)",
        "logo_icon": "Terminal",
        "description": "Collaborative problem solving, Azure distributed services, and reliable clean algorithms.",
        "community_tips": [
            "Microsoft interviewers appreciate candidates who explain their thought process out loud.",
            "Questions lean toward Linked Lists, Strings, Binary Search Trees, and System Design.",
            "Demonstrate growth mindset and willingness to learn from past debugging mistakes."
        ],
        "problems": [
            {"title": "Sign of the Product of an Array", "slug": "sign-of-product", "difficulty": "EASY", "frequency": 100, "topics": ["Array", "Math"], "order": 1, "is_unlocked": True},
            {"title": "Spiral Matrix II", "slug": "spiral-matrix-ii", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Array", "Matrix", "Simulation"], "order": 2, "is_unlocked": True},
            {"title": "Binary Tree Zigzag Level Order Traversal", "slug": "binary-tree-zigzag-level-order", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Tree", "BFS"], "order": 3, "is_unlocked": True},
            {"title": "Reverse Words in a String", "slug": "reverse-words-in-string", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Two Pointers", "String"], "order": 4, "is_unlocked": False},
            {"title": "Course Schedule", "slug": "course-schedule", "difficulty": "MEDIUM", "frequency": 87, "topics": ["DFS", "BFS", "Graph", "Topological Sort"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Atlassian",
        "slug": "atlassian",
        "tier": "silver",
        "role_title": "Software Engineer (P30/P40)",
        "logo_icon": "GitBranch",
        "description": "Jira & Confluence scale, rate limiting, and clean maintainable code craft.",
        "community_tips": [
            "Atlassian puts heavy weight on Code Craft: clean variable names, modular methods, and unit tests.",
            "Expect a real-world coding question like Rank Teams by Votes or Rate Limiter.",
            "Values alignment: 'Open company, no bullshit' means be completely honest about technical trade-offs."
        ],
        "problems": [
            {"title": "Rank Teams by Votes", "slug": "rank-teams-by-votes", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Array", "Hash Table", "String", "Sorting"], "order": 1, "is_unlocked": True},
            {"title": "Find All Possible Recipes from Given Supplies", "slug": "recipes-from-supplies", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Graph", "Topological Sort", "Hash Table"], "order": 2, "is_unlocked": True},
            {"title": "Design Snake Game", "slug": "design-snake-game", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Design", "Queue", "Array"], "order": 3, "is_unlocked": True},
            {"title": "Minimum Area Rectangle", "slug": "minimum-area-rectangle", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Hash Table", "Math", "Geometry"], "order": 4, "is_unlocked": False},
            {"title": "Logger Rate Limiter", "slug": "logger-rate-limiter", "difficulty": "EASY", "frequency": 86, "topics": ["Hash Table", "Design"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Bloomberg",
        "slug": "bloomberg",
        "tier": "silver",
        "role_title": "Software Engineer (Financial Core)",
        "logo_icon": "TrendingUp",
        "description": "Low-latency market ticker distribution, order books, and real-time streaming data.",
        "community_tips": [
            "Bloomberg loves Two Pointers, Stacks, Queues, and Leaderboard design.",
            "Demonstrate high fluency with standard libraries (C++ STL, Python collections).",
            "Explain how financial ticker streaming survives burst traffic spikes."
        ],
        "problems": [
            {"title": "Design Underground System", "slug": "design-underground-system", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Design", "Hash Table", "String"], "order": 1, "is_unlocked": True},
            {"title": "Invalid Transactions", "slug": "invalid-transactions", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Array", "Hash Table", "String", "Sorting"], "order": 2, "is_unlocked": True},
            {"title": "Flatten a Multilevel Doubly Linked List", "slug": "flatten-multilevel-doubly-linked-list", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Linked List", "DFS"], "order": 3, "is_unlocked": True},
            {"title": "Decode String", "slug": "decode-string", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Stack", "Recursion"], "order": 4, "is_unlocked": False},
            {"title": "Subsets", "slug": "subsets", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Array", "Backtracking"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Goldman Sachs",
        "slug": "goldman-sachs",
        "tier": "silver",
        "role_title": "Quantitative Developer & Platform Engineer",
        "logo_icon": "Briefcase",
        "description": "Financial risk engines, algorithmic trading, and mathematical precision.",
        "community_tips": [
            "Expect math-heavy coding: string compression, fraction to recurring decimal, and prime factorization.",
            "Write clean, defensively verified code that never throws unhandled division by zero.",
            "Be prepared for deep questions on Java GC or C++ memory layout."
        ],
        "problems": [
            {"title": "Fraction to Recurring Decimal", "slug": "fraction-to-recurring-decimal", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Math", "Hash Table", "String"], "order": 1, "is_unlocked": True},
            {"title": "High Five", "slug": "high-five", "difficulty": "EASY", "frequency": 95, "topics": ["Array", "Hash Table", "Sorting", "Heap"], "order": 2, "is_unlocked": True},
            {"title": "Knight Probability in Chessboard", "slug": "knight-probability-chessboard", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Dynamic Programming", "Probability"], "order": 3, "is_unlocked": True},
            {"title": "String Compression", "slug": "string-compression", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Two Pointers", "String"], "order": 4, "is_unlocked": False},
            {"title": "Minimum Size Subarray Sum", "slug": "minimum-size-subarray-sum", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "Binary Search", "Sliding Window"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Morgan Stanley",
        "slug": "morgan-stanley",
        "tier": "silver",
        "role_title": "Technology Analyst / SDE",
        "logo_icon": "Landmark",
        "description": "Institutional securities technology, high-reliability banking backends, and low latency.",
        "community_tips": [
            "Morgan Stanley focuses on Java fundamentals (OOP, multithreading, collections).",
            "Algorithms test Tree traversal, Dynamic Programming, and sorting algorithms.",
            "Be ready to discuss database ACID guarantees and distributed lock managers."
        ],
        "problems": [
            {"title": "Maximum Subarray", "slug": "maximum-subarray", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Array", "Divide and Conquer", "DP"], "order": 1, "is_unlocked": True},
            {"title": "Coin Change", "slug": "coin-change", "difficulty": "MEDIUM", "frequency": 94, "topics": ["DP", "BFS"], "order": 2, "is_unlocked": True},
            {"title": "Lowest Common Ancestor of a Binary Search Tree", "slug": "lca-bst", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Tree", "DFS", "BST"], "order": 3, "is_unlocked": True},
            {"title": "Validate Binary Search Tree", "slug": "validate-bst", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Tree", "DFS", "BST"], "order": 4, "is_unlocked": False},
            {"title": "Longest Common Subsequence", "slug": "longest-common-subsequence", "difficulty": "MEDIUM", "frequency": 85, "topics": ["DP", "String"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "LinkedIn",
        "slug": "linkedin",
        "tier": "silver",
        "role_title": "Software Engineer (Member Graph)",
        "logo_icon": "Users",
        "description": "Social graph indexing, Kafka streaming, and high-degree connection search.",
        "community_tips": [
            "LinkedIn loves graph traversal, shortest path, and combination sum problems.",
            "System design rounds focus heavily on Kafka, feed generation, and inverted indexes.",
            "Explain trade-offs between precomputed feeds and pull-on-read feeds."
        ],
        "problems": [
            {"title": "Can Place Flowers", "slug": "can-place-flowers", "difficulty": "EASY", "frequency": 96, "topics": ["Array", "Greedy"], "order": 1, "is_unlocked": True},
            {"title": "Find Leaves of Binary Tree", "slug": "find-leaves-of-binary-tree", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Tree", "DFS"], "order": 2, "is_unlocked": True},
            {"title": "Shortest Word Distance II", "slug": "shortest-word-distance-ii", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Hash Table", "Two Pointers", "Design"], "order": 3, "is_unlocked": True},
            {"title": "Max Points on a Line", "slug": "max-points-on-a-line", "difficulty": "HARD", "frequency": 87, "topics": ["Geometry", "Math", "Hash Table"], "order": 4, "is_unlocked": False},
            {"title": "Second Minimum Node In a Binary Tree", "slug": "second-min-node-binary-tree", "difficulty": "EASY", "frequency": 84, "topics": ["Tree", "DFS"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Salesforce",
        "slug": "salesforce",
        "tier": "silver",
        "role_title": "MTS (Member of Technical Staff)",
        "logo_icon": "Cloud",
        "description": "Multi-tenant enterprise CRM cloud, governor limits, and high-throughput query engines.",
        "community_tips": [
            "Salesforce questions test multi-tenant resource fairness and query optimization.",
            "Algorithms test Tree traversal, sliding windows, and topological sorting.",
            "Demonstrate understanding of REST API versioning and tenant isolation."
        ],
        "problems": [
            {"title": "Valid Parentheses", "slug": "valid-parentheses", "difficulty": "EASY", "frequency": 98, "topics": ["String", "Stack"], "order": 1, "is_unlocked": True},
            {"title": "Design Task Scheduler with Dependencies", "slug": "task-scheduler-dependencies", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Graph", "Topological Sort", "Design"], "order": 2, "is_unlocked": True},
            {"title": "Find Peak Element", "slug": "find-peak-element", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Array", "Binary Search"], "order": 3, "is_unlocked": True},
            {"title": "Merge Two Sorted Lists", "slug": "merge-two-sorted-lists", "difficulty": "EASY", "frequency": 88, "topics": ["Linked List", "Recursion"], "order": 4, "is_unlocked": False},
            {"title": "Word Search", "slug": "word-search", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Array", "Backtracking", "Matrix"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Nvidia",
        "slug": "nvidia",
        "tier": "silver",
        "role_title": "Deep Learning Systems Engineer",
        "logo_icon": "Cpu",
        "description": "CUDA kernel acceleration, tensor memory layouts, and high-performance drivers.",
        "community_tips": [
            "Expect rigorous probing into thread divergence, memory bandwidth, and SIMD/SIMT.",
            "Write optimal C++ or Python code without unnecessary memory allocations.",
            "Discuss GPU memory hierarchy (registers, shared memory, global memory) with confidence."
        ],
        "problems": [
            {"title": "Multiply Strings", "slug": "multiply-strings", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Math", "String", "Simulation"], "order": 1, "is_unlocked": True},
            {"title": "Bitwise AND of Numbers Range", "slug": "bitwise-and-numbers-range", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Bit Manipulation"], "order": 2, "is_unlocked": True},
            {"title": "Rotate Image", "slug": "rotate-image", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Array", "Math", "Matrix"], "order": 3, "is_unlocked": True},
            {"title": "Valid Sudoku", "slug": "valid-sudoku", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Array", "Hash Table", "Matrix"], "order": 4, "is_unlocked": False},
            {"title": "Single Number II", "slug": "single-number-ii", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Array", "Bit Manipulation"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Coinbase",
        "slug": "coinbase",
        "tier": "silver",
        "role_title": "Backend Blockchain & Ledger Engineer",
        "logo_icon": "Coins",
        "description": "Cryptographic double-entry accounting, order book matching engines, and zero-loss reliability.",
        "community_tips": [
            "Coinbase puts heavy weight on exact currency precision (no floating-point rounding errors).",
            "Expect practical machine coding: write an in-memory Limit Order Book matching engine.",
            "Security mindset is tested: how does your service guard against double-spending and replay attacks?"
        ],
        "problems": [
            {"title": "Design In-Memory Limit Order Book", "slug": "design-limit-order-book", "difficulty": "HARD", "frequency": 100, "topics": ["Design", "Heap", "Doubly-Linked List", "Hash Map"], "order": 1, "is_unlocked": True},
            {"title": "Convert Currency with Exchange Rates", "slug": "currency-exchange-rates", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Graph", "BFS", "DFS", "Shortest Path"], "order": 2, "is_unlocked": True},
            {"title": "Reconstruct Itinerary", "slug": "reconstruct-itinerary", "difficulty": "HARD", "frequency": 92, "topics": ["DFS", "Graph", "Eulerian Circuit"], "order": 3, "is_unlocked": True},
            {"title": "Accounts Merge", "slug": "accounts-merge", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Union Find", "DFS", "BFS"], "order": 4, "is_unlocked": False},
            {"title": "Meeting Rooms II", "slug": "meeting-rooms-ii", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "Two Pointers", "Sorting", "Heap"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Airbnb",
        "slug": "airbnb",
        "tier": "silver",
        "role_title": "Software Engineer (Guest Core)",
        "logo_icon": "Home",
        "description": "Search ranking, booking date overlaps, calendar synchronization, and review pipelines.",
        "community_tips": [
            "Airbnb focuses heavily on Interval problems and 2D Matrix traversal.",
            "Coding style is audited closely: write production-ready code with clean helper functions.",
            "In behavioral rounds, emphasize 'Host Mindset' and creating belonging anywhere."
        ],
        "problems": [
            {"title": "Insert Interval", "slug": "insert-interval", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Array"], "order": 1, "is_unlocked": True},
            {"title": "Alien Dictionary", "slug": "alien-dictionary-airbnb", "difficulty": "HARD", "frequency": 95, "topics": ["Graph", "Topological Sort"], "order": 2, "is_unlocked": True},
            {"title": "Text Justification", "slug": "text-justification", "difficulty": "HARD", "frequency": 92, "topics": ["Array", "String", "Simulation"], "order": 3, "is_unlocked": True},
            {"title": "Pour Water", "slug": "pour-water", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Array", "Simulation"], "order": 4, "is_unlocked": False},
            {"title": "Employee Free Time", "slug": "employee-free-time", "difficulty": "HARD", "frequency": 85, "topics": ["Array", "Sorting", "Heap"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Spotify",
        "slug": "spotify",
        "tier": "silver",
        "role_title": "Backend Engineer (Playback Core)",
        "logo_icon": "Music",
        "description": "Global audio CDN, personalized playlist recommendation sharding, and P2P distribution.",
        "community_tips": [
            "Spotify tests playback shuffle algorithms (Fisher-Yates) and LRU audio stream caching.",
            "Expect a strong collaborative interview where the engineer pairs with you on a problem.",
            "Discuss graceful degradation when playback servers face high network latency."
        ],
        "problems": [
            {"title": "Shuffle an Array (Fair Shuffle)", "slug": "shuffle-an-array", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Array", "Math", "Randomized"], "order": 1, "is_unlocked": True},
            {"title": "Design Audio Stream Ring Buffer", "slug": "design-ring-buffer", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Design", "Queue", "Array"], "order": 2, "is_unlocked": True},
            {"title": "Top K Frequent Elements", "slug": "top-k-frequent-elements", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Hash Table", "Heap", "Quickselect"], "order": 3, "is_unlocked": True},
            {"title": "Clone Graph", "slug": "clone-graph", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Hash Table", "BFS", "DFS", "Graph"], "order": 4, "is_unlocked": False},
            {"title": "Find the Duplicate Number", "slug": "find-duplicate-number", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Array", "Two Pointers", "Binary Search"], "order": 5, "is_unlocked": False},
        ]
    },

    # BRONZE TIER (16 companies)
    {
        "name": "Swiggy",
        "slug": "swiggy",
        "tier": "bronze",
        "role_title": "SDE-1/2 (Logistics & Fulfilment)",
        "logo_icon": "Bike",
        "description": "Hyperlocal delivery routing, peak hour order surge allocation, and low-latency pricing.",
        "community_tips": [
            "Swiggy asks practical DSA: BFS on delivery grids, sliding window cost minimization, and greedy intervals.",
            "In machine coding, write a mini delivery partner assignment engine with clean OOP principles.",
            "Expect questions on how to avoid race conditions when two customers order the last food item."
        ],
        "problems": [
            {"title": "Shortest Path in Binary Matrix", "slug": "shortest-path-binary-matrix", "difficulty": "MEDIUM", "frequency": 98, "topics": ["BFS", "Matrix"], "order": 1, "is_unlocked": True},
            {"title": "Maximum Units on a Truck", "slug": "maximum-units-truck", "difficulty": "EASY", "frequency": 95, "topics": ["Array", "Greedy", "Sorting"], "order": 2, "is_unlocked": True},
            {"title": "Find the City With Smallest Number of Neighbors", "slug": "find-city-smallest-neighbors", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Graph", "Floyd-Warshall", "Shortest Path"], "order": 3, "is_unlocked": True},
            {"title": "Daily Temperatures", "slug": "daily-temperatures", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Array", "Stack", "Monotonic Stack"], "order": 4, "is_unlocked": False},
            {"title": "Car Fleet", "slug": "car-fleet", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Array", "Stack", "Sorting", "Monotonic Stack"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Zomato",
        "slug": "zomato",
        "tier": "bronze",
        "role_title": "Software Development Engineer",
        "logo_icon": "Utensils",
        "description": "Food delivery search, restaurant geo-indexing, and real-time order tracking.",
        "community_tips": [
            "Focus on QuadTrees / Geo-hashing concepts for restaurant discovery.",
            "Coding rounds test Priority Queue (Heaps) and Dynamic Programming.",
            "Demonstrate clean modular coding with unit tests."
        ],
        "problems": [
            {"title": "K Closest Points to Origin", "slug": "k-closest-points", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Array", "Math", "Heap", "Quickselect"], "order": 1, "is_unlocked": True},
            {"title": "Design Food Rating System", "slug": "design-food-rating-system", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Design", "Hash Table", "Heap"], "order": 2, "is_unlocked": True},
            {"title": "Minimum Cost to Connect Sticks", "slug": "minimum-cost-connect-sticks", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Heap", "Greedy"], "order": 3, "is_unlocked": True},
            {"title": "Gas Station", "slug": "gas-station", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Array", "Greedy"], "order": 4, "is_unlocked": False},
            {"title": "Search Suggestions System", "slug": "search-suggestions-system", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Trie", "String", "Binary Search"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Flipkart",
        "slug": "flipkart",
        "tier": "bronze",
        "role_title": "SDE-1 (E-Commerce Platform)",
        "logo_icon": "ShoppingBag",
        "description": "Flash sale inventory isolation, warehouse rack optimization, and multi-round machine coding.",
        "community_tips": [
            "Flipkart's Machine Coding round is legendary: write fully working, extensible OOP code in 90 minutes.",
            "Enforce separation of concerns: Service layer, Repository layer, and Domain models.",
            "In DSA rounds, expect 1 Tree/Graph problem and 1 Hard Dynamic Programming puzzle."
        ],
        "problems": [
            {"title": "Design Inventory Reservation Engine (Flash Sale)", "slug": "design-inventory-reservation", "difficulty": "HARD", "frequency": 100, "topics": ["Design", "Hash Map", "Concurrency"], "order": 1, "is_unlocked": True},
            {"title": "Rotated Digits", "slug": "rotated-digits", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Math", "Dynamic Programming"], "order": 2, "is_unlocked": True},
            {"title": "Longest Increasing Subsequence", "slug": "longest-increasing-subsequence", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Array", "Binary Search", "DP"], "order": 3, "is_unlocked": True},
            {"title": "Coin Change 2", "slug": "coin-change-2", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Array", "Dynamic Programming"], "order": 4, "is_unlocked": False},
            {"title": "Jump Game II", "slug": "jump-game-ii", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "Dynamic Programming", "Greedy"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Razorpay",
        "slug": "razorpay",
        "tier": "bronze",
        "role_title": "Backend SDE (Fintech Core)",
        "logo_icon": "Zap",
        "description": "Payment gateway routing, bank webhook idempotency, and high-uptime settlement engines.",
        "community_tips": [
            "Heavy emphasis on distributed lock safety (Redis Redlock), idempotency keys, and reconciliation.",
            "Expect practical questions on state machines for payment transitions (CREATED -> AUTHORIZED -> CAPTURED).",
            "Be prepared to write clean concurrency-safe code in Python or Java."
        ],
        "problems": [
            {"title": "Design Payment State Machine with Webhook Replay", "slug": "design-payment-state-machine", "difficulty": "HARD", "frequency": 100, "topics": ["Design", "Hash Map", "State Machine"], "order": 1, "is_unlocked": True},
            {"title": "Subarray Sum Equals K", "slug": "subarray-sum-equals-k", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Array", "Hash Table", "Prefix Sum"], "order": 2, "is_unlocked": True},
            {"title": "Next Greater Element II", "slug": "next-greater-element-ii", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Array", "Stack", "Monotonic Stack"], "order": 3, "is_unlocked": True},
            {"title": "Partition Equal Subset Sum", "slug": "partition-equal-subset-sum", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Array", "DP"], "order": 4, "is_unlocked": False},
            {"title": "Maximal Square", "slug": "maximal-square", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Array", "DP", "Matrix"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Zepto",
        "slug": "zepto",
        "tier": "bronze",
        "role_title": "SDE-1 (Quick Commerce Systems)",
        "logo_icon": "Clock",
        "description": "10-minute dark store picker routing, hyper-local stock reservation, and real-time delivery optimization.",
        "community_tips": [
            "Zepto tests picker route optimization inside small dark store warehouses (Traveling Salesman / BFS).",
            "Speed of coding and high accuracy are prized.",
            "Machine coding tests building an in-memory Dark Store Inventory Management system."
        ],
        "problems": [
            {"title": "Dark Store Picker Route Shortest Path", "slug": "dark-store-picker-path", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Graph", "BFS", "Matrix", "Greedy"], "order": 1, "is_unlocked": True},
            {"title": "Meeting Rooms", "slug": "meeting-rooms", "difficulty": "EASY", "frequency": 94, "topics": ["Array", "Sorting"], "order": 2, "is_unlocked": True},
            {"title": "Capacity To Ship Packages Within D Days", "slug": "capacity-ship-packages", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Array", "Binary Search"], "order": 3, "is_unlocked": True},
            {"title": "Find All Anagrams in a String", "slug": "find-all-anagrams", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Hash Table", "String", "Sliding Window"], "order": 4, "is_unlocked": False},
            {"title": "Course Schedule IV", "slug": "course-schedule-iv", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Graph", "Topological Sort", "Floyd-Warshall"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "TCS Digital",
        "slug": "tcs-digital",
        "tier": "bronze",
        "role_title": "Digital Technology Cadre Engineer",
        "logo_icon": "GraduationCap",
        "description": "High-volume campus placement bar with strong emphasis on algorithmic foundations, strings, and OOP.",
        "community_tips": [
            "TCS Digital evaluates speed in dynamic programming and string manipulation.",
            "Write clean, standard C++/Java code without relying on complex external frameworks.",
            "In behavioral rounds, demonstrate project ownership and willingness to adapt to client domains."
        ],
        "problems": [
            {"title": "Longest Palindromic Substring", "slug": "longest-palindromic-substring", "difficulty": "MEDIUM", "frequency": 100, "topics": ["String", "Dynamic Programming"], "order": 1, "is_unlocked": True},
            {"title": "Climbing Stairs", "slug": "climbing-stairs", "difficulty": "EASY", "frequency": 96, "topics": ["Math", "Dynamic Programming", "Memoization"], "order": 2, "is_unlocked": True},
            {"title": "Two Sum", "slug": "two-sum", "difficulty": "EASY", "frequency": 93, "topics": ["Array", "Hash Table"], "order": 3, "is_unlocked": True},
            {"title": "Container With Most Water", "slug": "container-with-most-water", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Array", "Two Pointers", "Greedy"], "order": 4, "is_unlocked": False},
            {"title": "3Sum", "slug": "3sum", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Array", "Two Pointers", "Sorting"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Adobe",
        "slug": "adobe",
        "tier": "bronze",
        "role_title": "Member of Technical Staff",
        "logo_icon": "Sparkles",
        "description": "Creative Cloud rendering engines, PDF document structure parsing, and geometric algorithms.",
        "community_tips": [
            "Adobe questions frequently test String parsing, Trie search, and 2D Geometry.",
            "Expect 1 question on Linked Lists or Binary Trees and 1 question on Matrix manipulation.",
            "Discuss memory safety and buffer management in media rendering."
        ],
        "problems": [
            {"title": "Implement Trie (Prefix Tree)", "slug": "implement-trie", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Trie", "Design", "Hash Table"], "order": 1, "is_unlocked": True},
            {"title": "Copy List with Random Pointer", "slug": "copy-list-with-random-pointer", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Linked List", "Hash Table"], "order": 2, "is_unlocked": True},
            {"title": "LRU Cache", "slug": "lru-cache-adobe", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Hash Table", "Linked List", "Design"], "order": 3, "is_unlocked": True},
            {"title": "Set Matrix Zeroes", "slug": "set-matrix-zeroes", "difficulty": "MEDIUM", "frequency": 89, "topics": ["Array", "Hash Table", "Matrix"], "order": 4, "is_unlocked": False},
            {"title": "Flatten Binary Tree to Linked List", "slug": "flatten-binary-tree", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Linked List", "Tree", "DFS"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Oracle",
        "slug": "oracle",
        "tier": "silver",
        "role_title": "Member of Technical Staff (OCI)",
        "logo_icon": "Building2",
        "description": "Cloud infrastructure, storage engines, distributed transaction processing, and multi-tenant virtualization.",
        "community_tips": [
            "Heavy questioning on database internals, ACID vs BASE, and Paxos/Raft consensus.",
            "Expect low-level C++/Java memory management and lock-free concurrency questions."
        ],
        "problems": [
            {"title": "LRU Cache", "slug": "oracle-lru-cache", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Design", "Hash Table", "Linked List"], "order": 1, "is_unlocked": True},
            {"title": "Design In-Memory File System", "slug": "oracle-file-system", "difficulty": "HARD", "frequency": 92, "topics": ["Design", "Trie"], "order": 2, "is_unlocked": True},
            {"title": "Binary Tree Maximum Path Sum", "slug": "oracle-max-path-sum", "difficulty": "HARD", "frequency": 88, "topics": ["Tree", "DFS"], "order": 3, "is_unlocked": True},
            {"title": "Reorganize String", "slug": "oracle-reorganize-string", "difficulty": "MEDIUM", "frequency": 85, "topics": ["Heap", "Greedy"], "order": 4, "is_unlocked": False},
            {"title": "Course Schedule II", "slug": "oracle-course-schedule", "difficulty": "MEDIUM", "frequency": 82, "topics": ["Graph", "Topological Sort"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Cisco",
        "slug": "cisco",
        "tier": "bronze",
        "role_title": "Software Engineer (Networking & Cloud)",
        "logo_icon": "Building2",
        "description": "Network packet processing, socket programming, distributed telemetry, and router firmware.",
        "community_tips": [
            "Expect questions on IP routing, subnet masks, and bitwise manipulation.",
            "Commonly asks Graph traversal (BFS/Dijkstra) for network topology optimization."
        ],
        "problems": [
            {"title": "Network Delay Time", "slug": "cisco-network-delay-time", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Graph", "Dijkstra", "Heap"], "order": 1, "is_unlocked": True},
            {"title": "Number of Islands", "slug": "cisco-number-of-islands", "difficulty": "MEDIUM", "frequency": 93, "topics": ["DFS", "BFS", "Matrix"], "order": 2, "is_unlocked": True},
            {"title": "Reverse Linked List", "slug": "cisco-reverse-linked-list", "difficulty": "EASY", "frequency": 90, "topics": ["Linked List"], "order": 3, "is_unlocked": True},
            {"title": "Subarray Sum Equals K", "slug": "cisco-subarray-sum", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "Hash Table", "Prefix Sum"], "order": 4, "is_unlocked": False},
            {"title": "Longest Consecutive Sequence", "slug": "cisco-longest-consecutive", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Array", "Hash Table", "Union Find"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "PayPal",
        "slug": "paypal",
        "tier": "silver",
        "role_title": "Software Development Engineer",
        "logo_icon": "Building2",
        "description": "Global payment gateways, fraud detection pipelines, idempotency keys, and ledger reconciliation.",
        "community_tips": [
            "Interviews focus on transaction rollbacks, two-phase commits, and high-precision financial decimals.",
            "Be prepared to code a thread-safe currency exchange or rate limiter."
        ],
        "problems": [
            {"title": "Coin Change", "slug": "paypal-coin-change", "difficulty": "MEDIUM", "frequency": 98, "topics": ["DP", "BFS"], "order": 1, "is_unlocked": True},
            {"title": "Group Anagrams", "slug": "paypal-group-anagrams", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Array", "Hash Table", "String"], "order": 2, "is_unlocked": True},
            {"title": "Merge Intervals", "slug": "paypal-merge-intervals", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Array", "Sorting"], "order": 3, "is_unlocked": True},
            {"title": "Trapping Rain Water", "slug": "paypal-trapping-rain-water", "difficulty": "HARD", "frequency": 87, "topics": ["Two Pointers", "Stack"], "order": 4, "is_unlocked": False},
            {"title": "Decode String", "slug": "paypal-decode-string", "difficulty": "MEDIUM", "frequency": 84, "topics": ["Stack", "String", "Recursion"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Intuit",
        "slug": "intuit",
        "tier": "silver",
        "role_title": "Software Engineer (TurboTax & QuickBooks)",
        "logo_icon": "Building2",
        "description": "Rules engine processing, complex tax calculations, and real-time ledger accounting.",
        "community_tips": [
            "Intuit heavily evaluates clean code, object-oriented design patterns, and unit testability.",
            "Expect Tree and Graph questions simulating rule dependencies and deduction logic."
        ],
        "problems": [
            {"title": "Word Search", "slug": "intuit-word-search", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Array", "Backtracking", "Matrix"], "order": 1, "is_unlocked": True},
            {"title": "Validate Binary Search Tree", "slug": "intuit-validate-bst", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Tree", "DFS", "BST"], "order": 2, "is_unlocked": True},
            {"title": "Min Stack", "slug": "intuit-min-stack", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Stack", "Design"], "order": 3, "is_unlocked": True},
            {"title": "Top K Frequent Elements", "slug": "intuit-top-k-elements", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Hash Table", "Heap", "Quickselect"], "order": 4, "is_unlocked": False},
            {"title": "Reorder List", "slug": "intuit-reorder-list", "difficulty": "MEDIUM", "frequency": 82, "topics": ["Linked List", "Two Pointers"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Walmart Global Tech",
        "slug": "walmart",
        "tier": "silver",
        "role_title": "Software Development Engineer (Supply Chain)",
        "logo_icon": "Building2",
        "description": "Extreme retail scale: store inventory sync, route dispatch, catalog indexing, and flash checkout.",
        "community_tips": [
            "Expect Graph BFS/DFS questions for warehouse path finding and binary search on answers.",
            "Round 2 often tests low-level machine coding of an inventory management service."
        ],
        "problems": [
            {"title": "Rotting Oranges", "slug": "walmart-rotting-oranges", "difficulty": "MEDIUM", "frequency": 98, "topics": ["BFS", "Matrix"], "order": 1, "is_unlocked": True},
            {"title": "Lowest Common Ancestor of a Binary Tree", "slug": "walmart-lca-binary-tree", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Tree", "DFS"], "order": 2, "is_unlocked": True},
            {"title": "Kth Largest Element in an Array", "slug": "walmart-kth-largest", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Array", "Divide and Conquer", "Heap"], "order": 3, "is_unlocked": True},
            {"title": "Course Schedule", "slug": "walmart-course-schedule", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Graph", "Topological Sort"], "order": 4, "is_unlocked": False},
            {"title": "Median of Two Sorted Arrays", "slug": "walmart-median-two-sorted", "difficulty": "HARD", "frequency": 84, "topics": ["Array", "Binary Search"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Twitter / X",
        "slug": "twitter",
        "tier": "gold",
        "role_title": "Core Systems Engineer",
        "logo_icon": "Share2",
        "description": "Global pub-sub timeline fanout, Snowflake ID generation, and distributed caching.",
        "community_tips": [
            "Focus heavily on push vs pull fanout trade-offs for high-follower celebrity accounts.",
            "Fast algorithmic problem-solving with minimal memory footprint."
        ],
        "problems": [
            {"title": "Design Twitter", "slug": "twitter-design-twitter", "difficulty": "MEDIUM", "frequency": 100, "topics": ["Design", "Hash Table", "Linked List", "Heap"], "order": 1, "is_unlocked": True},
            {"title": "Insert Delete GetRandom O(1)", "slug": "twitter-random-set", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Array", "Hash Table", "Math", "Design"], "order": 2, "is_unlocked": True},
            {"title": "Merge k Sorted Lists", "slug": "twitter-merge-k-lists", "difficulty": "HARD", "frequency": 92, "topics": ["Linked List", "Heap", "Divide and Conquer"], "order": 3, "is_unlocked": True},
            {"title": "Sliding Window Maximum", "slug": "twitter-sliding-window-max", "difficulty": "HARD", "frequency": 88, "topics": ["Queue", "Sliding Window", "Monotonic Queue"], "order": 4, "is_unlocked": False},
            {"title": "LFU Cache", "slug": "twitter-lfu-cache", "difficulty": "HARD", "frequency": 85, "topics": ["Design", "Hash Table", "Doubly-Linked List"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Pinterest",
        "slug": "pinterest",
        "tier": "silver",
        "role_title": "Full Stack / Systems Engineer",
        "logo_icon": "Building2",
        "description": "Visual discovery, graph pinning relations, homefeed ranking, and image recommendation indexing.",
        "community_tips": [
            "Graph algorithms (Bipartite graphs, connected components) and Trie search are common.",
            "Expect a machine coding round on building a pinboard tagging and caching service."
        ],
        "problems": [
            {"title": "Word Break", "slug": "pinterest-word-break", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Hash Table", "String", "DP", "Trie"], "order": 1, "is_unlocked": True},
            {"title": "Is Graph Bipartite?", "slug": "pinterest-graph-bipartite", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Graph", "BFS", "DFS"], "order": 2, "is_unlocked": True},
            {"title": "Subsets", "slug": "pinterest-subsets", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Array", "Backtracking", "Bit Manipulation"], "order": 3, "is_unlocked": True},
            {"title": "Permutations", "slug": "pinterest-permutations", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "Backtracking"], "order": 4, "is_unlocked": False},
            {"title": "Longest Increasing Subsequence", "slug": "pinterest-lis", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Array", "Binary Search", "DP"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Snap",
        "slug": "snap",
        "tier": "gold",
        "role_title": "Software Engineer (Camera & Messaging)",
        "logo_icon": "Sparkles",
        "description": "Ephemeral media streaming, spatial mapping, and low-latency messaging protocols.",
        "community_tips": [
            "Expect hard DP and Sliding Window problems with real-time audio/video buffer constraints.",
            "Snap bar-raisers scrutinize time complexity down to microsecond CPU cycles."
        ],
        "problems": [
            {"title": "Minimum Window Substring", "slug": "snap-min-window-substring", "difficulty": "HARD", "frequency": 98, "topics": ["Hash Table", "String", "Sliding Window"], "order": 1, "is_unlocked": True},
            {"title": "Longest Substring Without Repeating Characters", "slug": "snap-longest-substring-non-repeat", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Hash Table", "String", "Sliding Window"], "order": 2, "is_unlocked": True},
            {"title": "Basic Calculator II", "slug": "snap-basic-calculator-ii", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Math", "String", "Stack"], "order": 3, "is_unlocked": True},
            {"title": "Edit Distance", "slug": "snap-edit-distance", "difficulty": "MEDIUM", "frequency": 88, "topics": ["String", "DP"], "order": 4, "is_unlocked": False},
            {"title": "Regular Expression Matching", "slug": "snap-regex-matching", "difficulty": "HARD", "frequency": 85, "topics": ["String", "DP", "Recursion"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Robinhood",
        "slug": "robinhood",
        "tier": "gold",
        "role_title": "Software Engineer (Trading Core)",
        "logo_icon": "Building2",
        "description": "High-frequency stock order matching engine, portfolio margins, and real-time WebSocket feeds.",
        "community_tips": [
            "Trading systems require 100% deterministic memory bounds and zero race conditions.",
            "Expect custom Tree/Heap design questions for limit order books."
        ],
        "problems": [
            {"title": "Design an In-Memory Order Book", "slug": "robinhood-order-book", "difficulty": "HARD", "frequency": 100, "topics": ["Design", "Heap", "Hash Table", "TreeMap"], "order": 1, "is_unlocked": True},
            {"title": "Best Time to Buy and Sell Stock with Cooldown", "slug": "robinhood-stock-cooldown", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Array", "DP"], "order": 2, "is_unlocked": True},
            {"title": "Exclusive Time of Functions", "slug": "robinhood-exclusive-time", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Array", "Stack"], "order": 3, "is_unlocked": True},
            {"title": "Accounts Merge", "slug": "robinhood-accounts-merge", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Array", "Hash Table", "String", "Union Find"], "order": 4, "is_unlocked": False},
            {"title": "Word Ladder", "slug": "robinhood-word-ladder", "difficulty": "HARD", "frequency": 85, "topics": ["Hash Table", "String", "BFS"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "DoorDash",
        "slug": "doordash",
        "tier": "gold",
        "role_title": "Software Engineer (Logistics & Routing)",
        "logo_icon": "Car",
        "description": "Dynamic restaurant-dasher dispatch, arrival time estimation, and real-time surge pricing.",
        "community_tips": [
            "Geospatial algorithms, BFS on weighted matrices, and Interval scheduling.",
            "Always state edge cases when dashers go offline mid-delivery."
        ],
        "problems": [
            {"title": "Maximum Profit in Job Scheduling", "slug": "doordash-max-profit-scheduling", "difficulty": "HARD", "frequency": 99, "topics": ["Array", "Binary Search", "DP"], "order": 1, "is_unlocked": True},
            {"title": "Minimum Difficulty of a Job Schedule", "slug": "doordash-min-difficulty-schedule", "difficulty": "HARD", "frequency": 95, "topics": ["Array", "DP"], "order": 2, "is_unlocked": True},
            {"title": "Shortest Path in a Grid with Obstacles Elimination", "slug": "doordash-shortest-path-obstacles", "difficulty": "HARD", "frequency": 92, "topics": ["Array", "BFS", "Matrix"], "order": 3, "is_unlocked": True},
            {"title": "Design Underground System", "slug": "doordash-underground-system", "difficulty": "MEDIUM", "frequency": 88, "topics": ["Design", "Hash Table", "String"], "order": 4, "is_unlocked": False},
            {"title": "Employee Free Time", "slug": "doordash-employee-free-time", "difficulty": "HARD", "frequency": 85, "topics": ["Array", "Heap", "Sorting"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Lyft",
        "slug": "lyft",
        "tier": "silver",
        "role_title": "Software Engineer (Marketplace Routing)",
        "logo_icon": "Car",
        "description": "Driver dispatch matching, shared rides pooling, and dynamic pricing elasticity.",
        "community_tips": [
            "Expect interval scheduling, graph shortest paths, and clean modular class design.",
            "Interviewers look for defensive programming around GPS inaccuracies."
        ],
        "problems": [
            {"title": "Design In-Memory File System", "slug": "lyft-file-system", "difficulty": "HARD", "frequency": 97, "topics": ["Design", "Trie"], "order": 1, "is_unlocked": True},
            {"title": "Asteroid Collision", "slug": "lyft-asteroid-collision", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Array", "Stack", "Simulation"], "order": 2, "is_unlocked": True},
            {"title": "Next Greater Element I", "slug": "lyft-next-greater", "difficulty": "EASY", "frequency": 90, "topics": ["Array", "Hash Table", "Stack", "Monotonic Stack"], "order": 3, "is_unlocked": True},
            {"title": "Daily Temperatures", "slug": "lyft-daily-temperatures", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "Stack", "Monotonic Stack"], "order": 4, "is_unlocked": False},
            {"title": "Gas Station", "slug": "lyft-gas-station", "difficulty": "MEDIUM", "frequency": 82, "topics": ["Array", "Greedy"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Shopify",
        "slug": "shopify",
        "tier": "silver",
        "role_title": "Developer (Commerce Infrastructure)",
        "logo_icon": "Package",
        "description": "Multi-tenant checkout engines, flash-sale traffic handling, and GraphQL commerce APIs.",
        "community_tips": [
            "Shopify pairs live with candidates: talk out loud constantly as you code.",
            "Heavy emphasis on maintainable Ruby/TypeScript/Go code over obscure bit hacks."
        ],
        "problems": [
            {"title": "Valid Parentheses", "slug": "shopify-valid-parentheses", "difficulty": "EASY", "frequency": 96, "topics": ["String", "Stack"], "order": 1, "is_unlocked": True},
            {"title": "Merge Two Sorted Lists", "slug": "shopify-merge-two-lists", "difficulty": "EASY", "frequency": 93, "topics": ["Linked List", "Recursion"], "order": 2, "is_unlocked": True},
            {"title": "Search in Rotated Sorted Array", "slug": "shopify-search-rotated", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Array", "Binary Search"], "order": 3, "is_unlocked": True},
            {"title": "Word Search II", "slug": "shopify-word-search-ii", "difficulty": "HARD", "frequency": 86, "topics": ["Array", "String", "Backtracking", "Trie", "Matrix"], "order": 4, "is_unlocked": False},
            {"title": "Binary Tree Level Order Traversal", "slug": "shopify-level-order", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Tree", "BFS"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Twilio",
        "slug": "twilio",
        "tier": "silver",
        "role_title": "Software Engineer (Telephony Core)",
        "logo_icon": "Building2",
        "description": "Global SMS delivery gateways, voice SIP trunking, and high-concurrency event ingestion.",
        "community_tips": [
            "Telephony requires rock-solid queueing, rate limiting, and backpressure handling.",
            "Expect Questions on sliding window rate limiting and distributed deduplication."
        ],
        "problems": [
            {"title": "Design Hit Counter", "slug": "twilio-design-hit-counter", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Design", "Queue", "Array"], "order": 1, "is_unlocked": True},
            {"title": "Letter Combinations of a Phone Number", "slug": "twilio-letter-combinations", "difficulty": "MEDIUM", "frequency": 95, "topics": ["Hash Table", "String", "Backtracking"], "order": 2, "is_unlocked": True},
            {"title": "Minimum Remove to Make Valid Parentheses", "slug": "twilio-min-remove-valid", "difficulty": "MEDIUM", "frequency": 91, "topics": ["String", "Stack"], "order": 3, "is_unlocked": True},
            {"title": "Kth Smallest Element in a BST", "slug": "twilio-kth-smallest-bst", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Tree", "DFS", "BST"], "order": 4, "is_unlocked": False},
            {"title": "Construct Binary Tree from Preorder and Inorder Traversal", "slug": "twilio-construct-tree", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Array", "Hash Table", "Divide and Conquer", "Tree"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Square / Block",
        "slug": "square",
        "tier": "silver",
        "role_title": "Software Engineer (Cash App & Terminal)",
        "logo_icon": "Building2",
        "description": "Point-of-sale hardware sync, peer-to-peer money transfers, and offline payment queues.",
        "community_tips": [
            "Block pairs extensively with the candidate in an IDE of their choice.",
            "Write clean modular code with comprehensive unit tests for edge cases."
        ],
        "problems": [
            {"title": "First Unique Character in a String", "slug": "square-first-unique-char", "difficulty": "EASY", "frequency": 97, "topics": ["Hash Table", "String", "Queue", "Counting"], "order": 1, "is_unlocked": True},
            {"title": "Subarray Sum Equals K", "slug": "square-subarray-sum-k", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Array", "Hash Table", "Prefix Sum"], "order": 2, "is_unlocked": True},
            {"title": "Decode Ways", "slug": "square-decode-ways", "difficulty": "MEDIUM", "frequency": 90, "topics": ["String", "DP"], "order": 3, "is_unlocked": True},
            {"title": "Maximal Square", "slug": "square-maximal-square", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "DP", "Matrix"], "order": 4, "is_unlocked": False},
            {"title": "Find Minimum in Rotated Sorted Array", "slug": "square-find-min-rotated", "difficulty": "MEDIUM", "frequency": 82, "topics": ["Array", "Binary Search"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "ServiceNow",
        "slug": "servicenow",
        "tier": "silver",
        "role_title": "Software Engineer (Enterprise Workflow)",
        "logo_icon": "Building2",
        "description": "Enterprise cloud workflows, relational record mapping, and table indexing under high volume.",
        "community_tips": [
            "Expect recursion, tree traversal, and linked list manipulation.",
            "Focus on clean object hierarchies and proper boundary checks."
        ],
        "problems": [
            {"title": "Binary Tree Inorder Traversal", "slug": "servicenow-inorder-traversal", "difficulty": "EASY", "frequency": 96, "topics": ["Stack", "Tree", "DFS"], "order": 1, "is_unlocked": True},
            {"title": "Add Two Numbers", "slug": "servicenow-add-two-numbers", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Linked List", "Math", "Recursion"], "order": 2, "is_unlocked": True},
            {"title": "Merge Intervals", "slug": "servicenow-merge-intervals", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Array", "Sorting"], "order": 3, "is_unlocked": True},
            {"title": "Longest Palindromic Substring", "slug": "servicenow-longest-palindrome", "difficulty": "MEDIUM", "frequency": 86, "topics": ["String", "DP"], "order": 4, "is_unlocked": False},
            {"title": "Flatten Nested List Iterator", "slug": "servicenow-nested-iterator", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Stack", "Tree", "Design", "Queue"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Qualtrics",
        "slug": "qualtrics",
        "tier": "bronze",
        "role_title": "Software Engineer (Experience Management)",
        "logo_icon": "Building2",
        "description": "High-volume survey data analytics, aggregation pipelines, and customer feedback indexing.",
        "community_tips": [
            "Questions focus on hash tables, string matching, and sorting algorithms.",
            "Emphasize clear communication and structured problem decomposition."
        ],
        "problems": [
            {"title": "Top K Frequent Words", "slug": "qualtrics-top-k-words", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Hash Table", "String", "Trie", "Sorting", "Heap"], "order": 1, "is_unlocked": True},
            {"title": "Valid Anagram", "slug": "qualtrics-valid-anagram", "difficulty": "EASY", "frequency": 94, "topics": ["Hash Table", "String", "Sorting"], "order": 2, "is_unlocked": True},
            {"title": "Contains Duplicate", "slug": "qualtrics-contains-duplicate", "difficulty": "EASY", "frequency": 90, "topics": ["Array", "Hash Table", "Sorting"], "order": 3, "is_unlocked": True},
            {"title": "Intersection of Two Arrays II", "slug": "qualtrics-intersection-arrays", "difficulty": "EASY", "frequency": 86, "topics": ["Array", "Hash Table", "Two Pointers", "Binary Search"], "order": 4, "is_unlocked": False},
            {"title": "Sort Colors", "slug": "qualtrics-sort-colors", "difficulty": "MEDIUM", "frequency": 82, "topics": ["Array", "Two Pointers", "Sorting"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Deliveroo",
        "slug": "deliveroo",
        "tier": "silver",
        "role_title": "Software Engineer (Hyperlocal Logistics)",
        "logo_icon": "Car",
        "description": "Hyperlocal restaurant delivery dispatch, rider ETA prediction, and kitchen capacity management.",
        "community_tips": [
            "Interview questions center on geospatial shortest paths, priority queues, and graph cycles.",
            "State how you handle edge cases like canceled orders while rider is in transit."
        ],
        "problems": [
            {"title": "Dijkstra Shortest Path on Grid", "slug": "deliveroo-shortest-path", "difficulty": "MEDIUM", "frequency": 98, "topics": ["Graph", "Dijkstra", "Heap"], "order": 1, "is_unlocked": True},
            {"title": "Meeting Rooms II", "slug": "deliveroo-meeting-rooms-ii", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Array", "Two Pointers", "Greedy", "Sorting", "Heap"], "order": 2, "is_unlocked": True},
            {"title": "Task Scheduler", "slug": "deliveroo-task-scheduler", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Array", "Hash Table", "Greedy", "Sorting", "Heap"], "order": 3, "is_unlocked": True},
            {"title": "Jump Game", "slug": "deliveroo-jump-game", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Array", "DP", "Greedy"], "order": 4, "is_unlocked": False},
            {"title": "Jump Game II", "slug": "deliveroo-jump-game-ii", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Array", "DP", "Greedy"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Grab",
        "slug": "grab",
        "tier": "silver",
        "role_title": "Software Engineer (Southeast Asia Superapp)",
        "logo_icon": "Car",
        "description": "Southeast Asia ride-hailing, food delivery, and digital banking transactions.",
        "community_tips": [
            "Heavy emphasis on Go/Java concurrency primitives, channels, and locks.",
            "Expect 1 hard Array/Binary Search question and 1 Graph traversal problem."
        ],
        "problems": [
            {"title": "Find Peak Element", "slug": "grab-find-peak-element", "difficulty": "MEDIUM", "frequency": 96, "topics": ["Array", "Binary Search"], "order": 1, "is_unlocked": True},
            {"title": "Combination Sum", "slug": "grab-combination-sum", "difficulty": "MEDIUM", "frequency": 93, "topics": ["Array", "Backtracking"], "order": 2, "is_unlocked": True},
            {"title": "Number of Connected Components in an Undirected Graph", "slug": "grab-connected-components", "difficulty": "MEDIUM", "frequency": 90, "topics": ["DFS", "BFS", "Union Find", "Graph"], "order": 3, "is_unlocked": True},
            {"title": "Target Sum", "slug": "grab-target-sum", "difficulty": "MEDIUM", "frequency": 86, "topics": ["Array", "DP", "Backtracking"], "order": 4, "is_unlocked": False},
            {"title": "Cheapest Flights Within K Stops", "slug": "grab-cheapest-flights", "difficulty": "MEDIUM", "frequency": 82, "topics": ["DP", "DFS", "BFS", "Graph", "Heap", "Shortest Path"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Gojek",
        "slug": "gojek",
        "tier": "silver",
        "role_title": "Product Engineer (Driver Platform)",
        "logo_icon": "Car",
        "description": "On-demand multi-service platform, routing matching, batch order allocation, and wallet sync.",
        "community_tips": [
            "Gojek is famous for thorough machine coding rounds: build clean, extensible domain entities.",
            "Follow TDD (Test-Driven Development) and write solid unit tests."
        ],
        "problems": [
            {"title": "Design a Parking Lot Machine Coding", "slug": "gojek-parking-lot", "difficulty": "MEDIUM", "frequency": 100, "topics": ["OOP", "Design", "Hash Table"], "order": 1, "is_unlocked": True},
            {"title": "Design Battleship Game", "slug": "gojek-battleship", "difficulty": "MEDIUM", "frequency": 95, "topics": ["OOP", "Design", "Matrix"], "order": 2, "is_unlocked": True},
            {"title": "Course Schedule II", "slug": "gojek-course-schedule-ii", "difficulty": "MEDIUM", "frequency": 91, "topics": ["Depth-First Search", "Breadth-First Search", "Graph", "Topological Sort"], "order": 3, "is_unlocked": True},
            {"title": "Snakes and Ladders", "slug": "gojek-snakes-and-ladders", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Array", "BFS", "Matrix"], "order": 4, "is_unlocked": False},
            {"title": "Bus Routes", "slug": "gojek-bus-routes", "difficulty": "HARD", "frequency": 84, "topics": ["Array", "Hash Table", "BFS"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "PhonePe",
        "slug": "phonepe",
        "tier": "silver",
        "role_title": "Software Engineer (UPI Platform)",
        "logo_icon": "Building2",
        "description": "High-volume UPI payment routing, transaction ledger, idempotency keys, and instant refunds.",
        "community_tips": [
            "PhonePe values deep algorithmic correctness and zero tolerance for currency rounding errors.",
            "Expect questions on sliding window maximum, monotonic queues, and interval trees."
        ],
        "problems": [
            {"title": "Sliding Window Maximum", "slug": "phonepe-sliding-window-max", "difficulty": "HARD", "frequency": 99, "topics": ["Array", "Queue", "Sliding Window", "Monotonic Queue", "Heap"], "order": 1, "is_unlocked": True},
            {"title": "Trapping Rain Water", "slug": "phonepe-trapping-rain-water", "difficulty": "HARD", "frequency": 95, "topics": ["Array", "Two Pointers", "Dynamic Programming", "Stack", "Monotonic Stack"], "order": 2, "is_unlocked": True},
            {"title": "Next Greater Element II", "slug": "phonepe-next-greater-ii", "difficulty": "MEDIUM", "frequency": 92, "topics": ["Array", "Stack", "Monotonic Stack"], "order": 3, "is_unlocked": True},
            {"title": "Minimum Knight Moves", "slug": "phonepe-knight-moves", "difficulty": "MEDIUM", "frequency": 88, "topics": ["BFS"], "order": 4, "is_unlocked": False},
            {"title": "Count of Smaller Numbers After Self", "slug": "phonepe-smaller-numbers", "difficulty": "HARD", "frequency": 84, "topics": ["Array", "Binary Search", "Divide and Conquer", "Binary Indexed Tree", "Segment Tree"], "order": 5, "is_unlocked": False},
        ]
    },
    {
        "name": "Meesho",
        "slug": "meesho",
        "tier": "bronze",
        "role_title": "SDE-1 (Search & Discovery)",
        "logo_icon": "Building2",
        "description": "Social commerce discovery, reseller product catalog, regional language search, and seller inventory.",
        "community_tips": [
            "Meesho has a dedicated Problem Solving round with 2 medium DSA questions in 45 minutes.",
            "Commonly tests Two Pointers, Dynamic Programming, and Binary Search on sorted ranges."
        ],
        "problems": [
            {"title": "Longest Repeating Character Replacement", "slug": "meesho-repeating-char-replace", "difficulty": "MEDIUM", "frequency": 97, "topics": ["Hash Table", "String", "Sliding Window"], "order": 1, "is_unlocked": True},
            {"title": "Search a 2D Matrix II", "slug": "meesho-search-2d-matrix-ii", "difficulty": "MEDIUM", "frequency": 94, "topics": ["Array", "Binary Search", "Divide and Conquer", "Matrix"], "order": 2, "is_unlocked": True},
            {"title": "Palindromic Substrings", "slug": "meesho-palindromic-substrings", "difficulty": "MEDIUM", "frequency": 90, "topics": ["Two Pointers", "String", "Dynamic Programming"], "order": 3, "is_unlocked": True},
            {"title": "Maximum Subarray", "slug": "meesho-max-subarray", "difficulty": "MEDIUM", "frequency": 87, "topics": ["Array", "Divide and Conquer", "Dynamic Programming"], "order": 4, "is_unlocked": False},
            {"title": "Merge Intervals", "slug": "meesho-merge-intervals", "difficulty": "MEDIUM", "frequency": 83, "topics": ["Array", "Sorting"], "order": 5, "is_unlocked": False},
        ]
    }
]

# PRESET PLACEMENT SIMULATIONS (Flagship Multi-Round Assessment Bundles)
PRESET_SIMULATIONS = [
    {
        "id": "google-sde-sim",
        "company": "Google",
        "title": "Google SDE Comprehensive Hiring Simulation",
        "tier": "gold",
        "logo_icon": "Search",
        "tagline": "3-Round Full Hiring Assessment (OA → Distributed Project → Google Scale Cross-Exam)",
        "duration_minutes": 85,
        "rounds": [
            {
                "round_number": 1,
                "name": "Round 1: Hard DSA Online Assessment",
                "type": "oa_dsa",
                "time_limit": 30,
                "problem": "Longest Increasing Path in a Matrix",
                "description": "Solve dynamic programming with DFS graph memoization under strict runtime limits."
            },
            {
                "round_number": 2,
                "name": "Round 2: Systems Coding Project",
                "type": "ai_project",
                "time_limit": 30,
                "problem": "Async Task Queue with Dead Letter Queue",
                "description": "Implement thread-safe async queue with exponential backoff and Pytest assertions."
            },
            {
                "round_number": 3,
                "name": "Round 3: Google Scale & Googleyness Technical Interview",
                "type": "tough_interview",
                "time_limit": 25,
                "problem": "Oral Cross-Examination + Google Distributed Architecture",
                "description": "Interviewer examines your Round 1 code for cheating/copy-paste, then grills you on scaling to 1 Billion users."
            }
        ]
    },
    {
        "id": "uber-sde-sim",
        "company": "Uber",
        "title": "Uber SDE Backend & Dispatch Simulation",
        "tier": "gold",
        "logo_icon": "Car",
        "tagline": "3-Round Full Hiring Assessment (Graph OA → Rate Limiter → Dispatch Cross-Exam)",
        "duration_minutes": 85,
        "rounds": [
            {
                "round_number": 1,
                "name": "Round 1: Uber Concurrency & Graph OA",
                "type": "oa_dsa",
                "time_limit": 30,
                "problem": "Alien Dictionary & Escape the Spreading Fire",
                "description": "Topological sorting and multi-source BFS under dynamic obstacle spread."
            },
            {
                "round_number": 2,
                "name": "Round 2: Systems Coding Project",
                "type": "ai_project",
                "time_limit": 30,
                "problem": "Distributed Rate Limiter (Token Bucket & Sliding Window)",
                "description": "Build high-throughput rate limiter with Redis-like semantics and concurrent lock safety."
            },
            {
                "round_number": 3,
                "name": "Round 3: Uber Geospatial Dispatch & Concurrency Interview",
                "type": "tough_interview",
                "time_limit": 25,
                "problem": "Round 1 Code Verification + Geospatial Surge Dispatching",
                "description": "Defend your algorithmic choices in Round 1 and architect driver dispatching under 500k QPS."
            }
        ]
    },
    {
        "id": "openai-ai-engineer-sim",
        "company": "OpenAI",
        "title": "OpenAI AI Systems Engineer Simulation",
        "tier": "gold",
        "logo_icon": "Sparkles",
        "tagline": "3-Round Full Hiring Assessment (Matrix Optimization → Async Queue → OpenAI Scale Interview)",
        "duration_minutes": 85,
        "rounds": [
            {
                "round_number": 1,
                "name": "Round 1: Matrix / Trie Optimization OA",
                "type": "oa_dsa",
                "time_limit": 30,
                "problem": "LRU Cache with Memory Budget & Stream of Characters",
                "description": "Design sub-millisecond memory-bounded token lookups and prefix matching."
            },
            {
                "round_number": 2,
                "name": "Round 2: Systems Coding Project",
                "type": "ai_project",
                "time_limit": 30,
                "problem": "Async Worker & GPU Batching Engine",
                "description": "Build high-throughput batching queue with priority job preemption and health checks."
            },
            {
                "round_number": 3,
                "name": "Round 3: OpenAI Scale LLM Streaming & Alignment Interview",
                "type": "tough_interview",
                "time_limit": 25,
                "problem": "Round 1 Code Cross-Examination + 'Why OpenAI?' & 100M Token Streaming",
                "description": "Rigorous questioning on token streaming architectures, hallucination detection, and OpenAI mission alignment."
            }
        ]
    }
]

class CompanyRegistry:
    @classmethod
    def get_all_companies(cls) -> List[Dict[str, Any]]:
        return COMPANIES_50

    @classmethod
    def get_company_by_slug(cls, slug: str) -> Optional[Dict[str, Any]]:
        for comp in COMPANIES_50:
            if comp["slug"].lower() == slug.lower():
                return comp
        return None

    @classmethod
    def get_all_simulations(cls) -> List[Dict[str, Any]]:
        return PRESET_SIMULATIONS

    @classmethod
    def get_simulation_by_id(cls, sim_id: str) -> Optional[Dict[str, Any]]:
        for sim in PRESET_SIMULATIONS:
            if sim["id"] == sim_id:
                return sim
        return None
