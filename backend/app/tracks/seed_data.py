from typing import Any, Dict, List

TRACKS_SEED_DATA: List[Dict[str, Any]] = [
    # GOLD MINE
    {
        "name": "Uber",
        "slug": "uber",
        "tier": "gold",
        "role_title": "SDE-1 Backend & Systems Engineer",
        "description": "Prepare for Uber's notoriously rigorous engineering bar with a heavy focus on graph traversal, concurrency primitives, and distributed dispatch algorithms.",
        "logo_icon": "Car",
        "community_tips": [
            "Uber bar-raisers heavily penalize global state and hand-waving thread safety. Use granular concurrency controls and optimistic locking.",
            "Machine coding rounds expect clean modular interface separation and real unit tests, not just a single script.",
            "Expect 1 deep Graph/Topological Sort question and 1 Rate Limiter / Cache design question in the technical rounds."
        ],
        "problems": [
            {
                "title": "Escape the Spreading Fire",
                "slug": "escape-the-spreading-fire",
                "difficulty": "HARD",
                "frequency_score": 100.0,
                "acceptance_rate": 0.35,
                "topics": ["Array", "Binary Search", "Breadth-First Search", "Matrix"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "You are given a 2D grid of size m x n. Cells can be empty (0), fire (1), or a wall (2). You start at the top-left (0,0) and want to reach the safehouse at (m-1, n-1). Fire spreads to adjacent cells every minute. Determine the maximum number of minutes you can stay in place at the start before moving and still reach the safehouse without catching fire.",
                "starter_code": {
                    "python": "class Solution:\n    def maximumMinutes(self, grid: list[list[int]]) -> int:\n        # Write your solution here\n        pass\n",
                    "java": "class Solution {\n    public int maximumMinutes(int[][] grid) {\n        // Write your solution here\n        return 0;\n    }\n}\n",
                    "cpp": "#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    int maximumMinutes(vector<vector<int>>& grid) {\n        // Write your solution here\n        return 0;\n    }\n};\n"
                },
                "test_cases": [
                    {"input": "grid = [[0,2,0,0,0,0,0],[0,0,0,2,2,1,0],[0,2,0,0,1,2,0],[0,0,2,2,2,0,2],[0,0,0,0,0,0,0]]", "expected": "3"}
                ]
            },
            {
                "title": "Alien Dictionary",
                "slug": "alien-dictionary",
                "difficulty": "HARD",
                "frequency_score": 98.0,
                "acceptance_rate": 0.36,
                "topics": ["Array", "String", "Depth-First Search", "Breadth-First Search", "Graph Theory", "Topological Sort"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "There is a new alien language that uses the Latin alphabet. However, the order of letters is unknown. You receive a list of non-empty words from the alien language's dictionary, sorted lexicographically. Derive the order of letters in this language. If the order is invalid, return \"\".",
                "starter_code": {
                    "python": "class Solution:\n    def alienOrder(self, words: list[str]) -> str:\n        # Write your solution here\n        pass\n",
                    "java": "class Solution {\n    public String alienOrder(String[] words) {\n        return \"\";\n    }\n}\n",
                    "cpp": "#include <vector>\n#include <string>\nusing namespace std;\n\nclass Solution {\npublic:\n    string alienOrder(vector<string>& words) {\n        return \"\";\n    }\n};\n"
                },
                "test_cases": [
                    {"input": "words = [\"wrt\",\"wrf\",\"er\",\"ett\",\"rftt\"]", "expected": "\"wertf\""}
                ]
            },
            {
                "title": "Number of Islands II",
                "slug": "number-of-islands-ii",
                "difficulty": "HARD",
                "frequency_score": 95.0,
                "acceptance_rate": 0.39,
                "topics": ["Array", "Hash Table", "Union-Find"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "You are given an empty 2D grid of size m x n. An array positions where positions[i] = [ri, ci] indicates that at step i, an island appears at (ri, ci). Return an array representing the number of islands after each operation.",
                "starter_code": {
                    "python": "class Solution:\n    def numIslands2(self, m: int, n: int, positions: list[list[int]]) -> list[int]:\n        # Write your solution here\n        pass\n",
                    "java": "class Solution {\n    public List<Integer> numIslands2(int m, int n, int[][] positions) {\n        return new ArrayList<>();\n    }\n}\n",
                    "cpp": "#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> numIslands2(int m, int n, vector<vector<int>>& positions) {\n        return {};\n    }\n};\n"
                },
                "test_cases": [
                    {"input": "m = 3, n = 3, positions = [[0,0],[0,1],[1,2],[2,1]]", "expected": "[1,1,2,3]"}
                ]
            },
            {
                "title": "Minimum Number of Refueling Stops",
                "slug": "minimum-number-of-refueling-stops",
                "difficulty": "HARD",
                "frequency_score": 90.0,
                "acceptance_rate": 0.40,
                "topics": ["Array", "Dynamic Programming", "Greedy", "Heap (Priority Queue)"],
                "order_index": 4,
                "is_initially_unlocked": False,
                "description": "A car travels from a starting position to a destination which is target miles east. Along the way, there are gas stations. Return the minimum number of refueling stops to reach target. If impossible, return -1.",
                "starter_code": {
                    "python": "class Solution:\n    def minRefuelStops(self, target: int, startFuel: int, stations: list[list[int]]) -> int:\n        pass\n"
                },
                "test_cases": [{"input": "target = 100, startFuel = 10, stations = [[10,60],[20,30],[30,30],[60,40]]", "expected": "2"}]
            },
            {
                "title": "Design In-Memory File System",
                "slug": "design-in-memory-file-system",
                "difficulty": "HARD",
                "frequency_score": 88.0,
                "acceptance_rate": 0.48,
                "topics": ["Design", "Trie", "Hash Table", "String"],
                "order_index": 5,
                "is_initially_unlocked": False,
                "description": "Design an in-memory file system to simulate: ls, mkdir, addContentToFile, and readContentFromFile.",
                "starter_code": {
                    "python": "class FileSystem:\n    def __init__(self):\n        pass\n"
                },
                "test_cases": [{"input": "[\"FileSystem\",\"ls\",\"mkdir\",\"addContentToFile\",\"ls\",\"readContentFromFile\"]", "expected": "[null,[],null,null,[\"a\"],\"hello\"]"}]
            }
        ]
    },

    # GOOGLE
    {
        "name": "Google",
        "slug": "google",
        "tier": "gold",
        "role_title": "Software Engineer (L3/L4 Generalist)",
        "description": "Master algorithmic precision with Google's classic focus on dynamic programming, state-space exploration, and rigorous complexity bounds.",
        "logo_icon": "Search",
        "community_tips": [
            "Google interviewers probe scalability and mathematical proofs of time/space complexity before you start typing.",
            "Communicate your thought process loudly. Silence for more than 2 minutes is scored negatively.",
            "Expect non-standard variations of classic graph algorithms like Dijkstra with multi-dimensional states or 2D DP."
        ],
        "problems": [
            {
                "title": "Trapping Rain Water",
                "slug": "trapping-rain-water",
                "difficulty": "HARD",
                "frequency_score": 100.0,
                "acceptance_rate": 0.62,
                "topics": ["Array", "Two Pointers", "Dynamic Programming", "Stack", "Monotonic Stack"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.",
                "starter_code": {
                    "python": "class Solution:\n    def trap(self, height: list[int]) -> int:\n        # Two pointers or monotonic stack approach\n        pass\n",
                    "java": "class Solution {\n    public int trap(int[] height) {\n        return 0;\n    }\n}\n",
                    "cpp": "#include <vector>\nusing namespace std;\nclass Solution {\npublic:\n    int trap(vector<int>& height) {\n        return 0;\n    }\n};\n"
                },
                "test_cases": [
                    {"input": "height = [0,1,0,2,1,0,1,3,2,1,2,1]", "expected": "6"},
                    {"input": "height = [4,2,0,3,2,5]", "expected": "9"}
                ]
            },
            {
                "title": "Word Ladder",
                "slug": "word-ladder",
                "difficulty": "HARD",
                "frequency_score": 97.0,
                "acceptance_rate": 0.38,
                "topics": ["Hash Table", "String", "Breadth-First Search"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given two words, beginWord and endWord, and a dictionary wordList, return the number of words in the shortest transformation sequence from beginWord to endWord, or 0 if no such sequence exists.",
                "starter_code": {
                    "python": "class Solution:\n    def ladderLength(self, beginWord: str, endWord: str, wordList: list[str]) -> int:\n        pass\n"
                },
                "test_cases": [
                    {"input": "beginWord = \"hit\", endWord = \"cog\", wordList = [\"hot\",\"dot\",\"dog\",\"lot\",\"log\",\"cog\"]", "expected": "5"}
                ]
            },
            {
                "title": "Longest Increasing Path in a Matrix",
                "slug": "longest-increasing-path-in-a-matrix",
                "difficulty": "HARD",
                "frequency_score": 93.0,
                "acceptance_rate": 0.53,
                "topics": ["Array", "Dynamic Programming", "Depth-First Search", "Breadth-First Search", "Graph Theory", "Topological Sort", "Memoization"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "Given an m x n integers matrix, return the length of the longest increasing path in matrix. From each cell, you can move four directions: left, right, up, or down.",
                "starter_code": {
                    "python": "class Solution:\n    def longestIncreasingPath(self, matrix: list[list[int]]) -> int:\n        pass\n"
                },
                "test_cases": [
                    {"input": "matrix = [[9,9,4],[6,6,8],[2,1,1]]", "expected": "4"}
                ]
            },
            {
                "title": "Median of Two Sorted Arrays",
                "slug": "median-of-two-sorted-arrays",
                "difficulty": "HARD",
                "frequency_score": 89.0,
                "acceptance_rate": 0.40,
                "topics": ["Array", "Binary Search", "Divide and Conquer"],
                "order_index": 4,
                "is_initially_unlocked": False,
                "description": "Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays in O(log(m+n)) runtime.",
                "starter_code": {"python": "class Solution:\n    def findMedianSortedArrays(self, nums1: list[int], nums2: list[int]) -> float:\n        pass\n"},
                "test_cases": [{"input": "nums1 = [1,3], nums2 = [2]", "expected": "2.0"}]
            }
        ]
    },

    # AMAZON
    {
        "name": "Amazon",
        "slug": "amazon",
        "tier": "gold",
        "role_title": "SDE-1 / SDE Intern",
        "description": "Master high-frequency AWS/Amazon interview patterns with a 50/50 balance between heap/queue algorithms and Leadership Principles defense.",
        "logo_icon": "Package",
        "community_tips": [
            "Amazon strictly dedicates 20–25 minutes to Leadership Principles using the STAR method before coding.",
            "Have 2 distinct project stories prepared for 'Customer Obsession', 'Ownership', and 'Invent & Simplify'.",
            "Coding questions often revolve around Heap/PriorityQueue, Sliding Window, and Tree optimization."
        ],
        "problems": [
            {
                "title": "LRU Cache",
                "slug": "lru-cache",
                "difficulty": "MEDIUM",
                "frequency_score": 100.0,
                "acceptance_rate": 0.42,
                "topics": ["Hash Table", "Linked List", "Design", "Doubly-Linked List"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache. Implement LRUCache class with get(key) and put(key, value) in O(1) average time complexity.",
                "starter_code": {
                    "python": "class LRUCache:\n    def __init__(self, capacity: int):\n        pass\n    def get(self, key: int) -> int:\n        return -1\n    def put(self, key: int, value: int) -> None:\n        pass\n"
                },
                "test_cases": [
                    {"input": "[\"LRUCache\",\"put\",\"put\",\"get\",\"put\",\"get\",\"put\",\"get\",\"get\",\"get\"], [[2],[1,1],[2,2],[1],[3,3],[2],[4,4],[1],[3],[4]]", "expected": "[null,null,null,1,null,-1,null,-1,3,4]"}
                ]
            },
            {
                "title": "Reorganize String",
                "slug": "reorganize-string",
                "difficulty": "MEDIUM",
                "frequency_score": 96.0,
                "acceptance_rate": 0.54,
                "topics": ["Hash Table", "String", "Greedy", "Sorting", "Heap (Priority Queue)", "Counting"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given a string s, rearrange the characters of s so that any two adjacent characters are not the same. Return any possible rearrangement, or \"\" if not possible.",
                "starter_code": {
                    "python": "class Solution:\n    def reorganizeString(self, s: str) -> str:\n        pass\n"
                },
                "test_cases": [
                    {"input": "s = \"aab\"", "expected": "\"aba\""},
                    {"input": "s = \"aaab\"", "expected": "\"\""}
                ]
            },
            {
                "title": "Rotting Oranges",
                "slug": "rotting-oranges",
                "difficulty": "MEDIUM",
                "frequency_score": 95.0,
                "acceptance_rate": 0.55,
                "topics": ["Array", "Breadth-First Search", "Matrix"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "You are given an m x n grid where 0 is empty, 1 is fresh orange, and 2 is rotten orange. Every minute, any fresh orange that is 4-directionally adjacent to a rotten orange becomes rotten. Return the minimum number of minutes that must elapse until no cell has a fresh orange, or -1.",
                "starter_code": {
                    "python": "class Solution:\n    def orangesRotting(self, grid: list[list[int]]) -> int:\n        pass\n"
                },
                "test_cases": [
                    {"input": "grid = [[2,1,1],[1,1,0],[0,1,1]]", "expected": "4"}
                ]
            },
            {
                "title": "K Closest Points to Origin",
                "slug": "k-closest-points-to-origin",
                "difficulty": "MEDIUM",
                "frequency_score": 91.0,
                "acceptance_rate": 0.66,
                "topics": ["Array", "Math", "Divide and Conquer", "Geometry", "Sorting", "Heap (Priority Queue)", "Quickselect"],
                "order_index": 4,
                "is_initially_unlocked": False,
                "description": "Given an array of points where points[i] = [xi, yi] and an integer k, return the k closest points to the origin (0, 0).",
                "starter_code": {"python": "class Solution:\n    def kClosest(self, points: list[list[int]], k: int) -> list[list[int]]:\n        pass\n"},
                "test_cases": [{"input": "points = [[1,3],[-2,2]], k = 1", "expected": "[[-2,2]]"}]
            }
        ]
    },

    # MICROSOFT
    {
        "name": "Microsoft",
        "slug": "microsoft",
        "tier": "gold",
        "role_title": "Software Engineer (Cloud & Enterprise)",
        "description": "Enterprise-grade problem solving with sharp focus on trees, interval scheduling, and clean production code.",
        "logo_icon": "Layers",
        "community_tips": [
            "Microsoft loves clean, production-ready code with edge case checks (null inputs, empty arrays, integer overflows).",
            "Be ready to explain how your solution behaves in a microservice environment."
        ],
        "problems": [
            {
                "title": "Group Anagrams",
                "slug": "group-anagrams",
                "difficulty": "MEDIUM",
                "frequency_score": 99.0,
                "acceptance_rate": 0.67,
                "topics": ["Array", "Hash Table", "String", "Sorting"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Given an array of strings strs, group the anagrams together. You can return the answer in any order.",
                "starter_code": {"python": "class Solution:\n    def groupAnagrams(self, strs: list[str]) -> list[list[str]]:\n        pass\n"},
                "test_cases": [{"input": "strs = [\"eat\",\"tea\",\"tan\",\"ate\",\"nat\",\"bat\"]", "expected": "[[\"bat\"],[\"nat\",\"tan\"],[\"ate\",\"eat\",\"tea\"]]"}]
            },
            {
                "title": "Merge Intervals",
                "slug": "merge-intervals",
                "difficulty": "MEDIUM",
                "frequency_score": 97.0,
                "acceptance_rate": 0.47,
                "topics": ["Array", "Sorting"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given an array of intervals where intervals[i] = [starti, endi], merge all overlapping intervals and return an array of non-overlapping intervals.",
                "starter_code": {"python": "class Solution:\n    def merge(self, intervals: list[list[int]]) -> list[list[int]]:\n        pass\n"},
                "test_cases": [{"input": "intervals = [[1,3],[2,6],[8,10],[15,18]]", "expected": "[[1,6],[8,10],[15,18]]"}]
            },
            {
                "title": "Lowest Common Ancestor of a Binary Tree",
                "slug": "lowest-common-ancestor-of-a-binary-tree",
                "difficulty": "MEDIUM",
                "frequency_score": 94.0,
                "acceptance_rate": 0.61,
                "topics": ["Tree", "Depth-First Search", "Binary Tree"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "Given a binary tree, find the lowest common ancestor (LCA) of two given nodes in the tree.",
                "starter_code": {"python": "class Solution:\n    def lowestCommonAncestor(self, root, p, q):\n        pass\n"},
                "test_cases": [{"input": "root = [3,5,1,6,2,0,8,null,null,7,4], p = 5, q = 1", "expected": "3"}]
            }
        ]
    },

    # META
    {
        "name": "Meta",
        "slug": "meta",
        "tier": "gold",
        "role_title": "Software Engineer (Full Stack & Systems)",
        "description": "High-velocity coding rounds testing prefix sums, binary search variations, and tree serialization within 35 minutes.",
        "logo_icon": "Share2",
        "community_tips": [
            "Meta technical interviews expect optimal solutions to 2 Medium problems within 35 minutes.",
            "Speed and bug-free first-time execution are critical for Meta rounds."
        ],
        "problems": [
            {
                "title": "Subarray Sum Equals K",
                "slug": "subarray-sum-equals-k",
                "difficulty": "MEDIUM",
                "frequency_score": 100.0,
                "acceptance_rate": 0.44,
                "topics": ["Array", "Hash Table", "Prefix Sum"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Given an array of integers nums and an integer k, return the total number of subarrays whose sum equals to k.",
                "starter_code": {"python": "class Solution:\n    def subarraySum(self, nums: list[int], k: int) -> int:\n        pass\n"},
                "test_cases": [{"input": "nums = [1,1,1], k = 2", "expected": "2"}]
            },
            {
                "title": "Dot Product of Two Sparse Vectors",
                "slug": "dot-product-of-two-sparse-vectors",
                "difficulty": "MEDIUM",
                "frequency_score": 96.0,
                "acceptance_rate": 0.90,
                "topics": ["Array", "Hash Table", "Two Pointers", "Design"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given two sparse vectors, compute their dot product. Represent sparse vectors efficiently and calculate dot product in O(min(non_zeros)).",
                "starter_code": {"python": "class SparseVector:\n    def __init__(self, nums: list[int]):\n        pass\n    def dotProduct(self, vec: 'SparseVector') -> int:\n        return 0\n"},
                "test_cases": [{"input": "nums1 = [1,0,0,2,3], nums2 = [0,3,0,4,0]", "expected": "8"}]
            },
            {
                "title": "Valid Palindrome II",
                "slug": "valid-palindrome-ii",
                "difficulty": "EASY",
                "frequency_score": 92.0,
                "acceptance_rate": 0.40,
                "topics": ["Two Pointers", "String", "Greedy"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "Given a string s, return true if the s can be palindrome after deleting at most one character from it.",
                "starter_code": {"python": "class Solution:\n    def validPalindrome(self, s: str) -> bool:\n        pass\n"},
                "test_cases": [{"input": "s = \"aba\"", "expected": "true"}, {"input": "s = \"abca\"", "expected": "true"}]
            }
        ]
    },

    # SILVER MINE
    {
        "name": "Adobe",
        "slug": "adobe",
        "tier": "silver",
        "role_title": "Member of Technical Staff",
        "description": "Targeted practice for Adobe campus and lateral drives focusing on dynamic programming and string algorithms.",
        "logo_icon": "FileText",
        "community_tips": [
            "Adobe asks foundational data structures with heavy emphasis on linked lists, recursion, and string manipulation."
        ],
        "problems": [
            {
                "title": "Maximum Subarray",
                "slug": "maximum-subarray",
                "difficulty": "MEDIUM",
                "frequency_score": 95.0,
                "acceptance_rate": 0.51,
                "topics": ["Array", "Divide and Conquer", "Dynamic Programming"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Given an integer array nums, find the subarray with the largest sum, and return its sum (Kadane's algorithm).",
                "starter_code": {"python": "class Solution:\n    def maxSubArray(self, nums: list[int]) -> int:\n        pass\n"},
                "test_cases": [{"input": "nums = [-2,1,-3,4,-1,2,1,-5,4]", "expected": "6"}]
            },
            {
                "title": "Word Search",
                "slug": "word-search",
                "difficulty": "MEDIUM",
                "frequency_score": 90.0,
                "acceptance_rate": 0.41,
                "topics": ["Array", "String", "Backtracking", "Matrix"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given an m x n grid of characters board and a string word, return true if word exists in the grid.",
                "starter_code": {"python": "class Solution:\n    def exist(self, board: list[list[str]], word: str) -> bool:\n        pass\n"},
                "test_cases": [{"input": "board = [[\"A\",\"B\",\"C\",\"E\"],[\"S\",\"F\",\"C\",\"S\"],[\"A\",\"D\",\"E\",\"E\"]], word = \"ABCCED\"", "expected": "true"}]
            },
            {
                "title": "Search in Rotated Sorted Array",
                "slug": "search-in-rotated-sorted-array",
                "difficulty": "MEDIUM",
                "frequency_score": 88.0,
                "acceptance_rate": 0.40,
                "topics": ["Array", "Binary Search"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "Given the array nums after the possible rotation and an integer target, return the index of target if it is in nums, or -1 if it is not in nums.",
                "starter_code": {"python": "class Solution:\n    def search(self, nums: list[int], target: int) -> int:\n        pass\n"},
                "test_cases": [{"input": "nums = [4,5,6,7,0,1,2], target = 0", "expected": "4"}]
            }
        ]
    },
    {
        "name": "Atlassian",
        "slug": "atlassian",
        "tier": "silver",
        "role_title": "Software Engineer (Jira & Confluence)",
        "description": "Clean object-oriented system design and real-world concurrency management tailored to Atlassian's interview loop.",
        "logo_icon": "Compass",
        "community_tips": [
            "Atlassian machine coding and systems rounds focus on clean OOP design patterns and concurrency."
        ],
        "problems": [
            {
                "title": "Design Hit Counter",
                "slug": "design-hit-counter",
                "difficulty": "MEDIUM",
                "frequency_score": 96.0,
                "acceptance_rate": 0.69,
                "topics": ["Design", "Queue", "Array", "Binary Search"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Design a hit counter which counts the number of hits received in the past 5 minutes (300 seconds).",
                "starter_code": {"python": "class HitCounter:\n    def __init__(self):\n        pass\n    def hit(self, timestamp: int) -> None:\n        pass\n    def getHits(self, timestamp: int) -> int:\n        return 0\n"},
                "test_cases": [{"input": "[\"HitCounter\",\"hit\",\"hit\",\"hit\",\"getHits\",\"hit\",\"getHits\",\"getHits\"], [[],[1],[2],[3],[300],[300],[300],[301]]", "expected": "[null,null,null,null,3,null,4,3]"}]
            },
            {
                "title": "Meeting Rooms II",
                "slug": "meeting-rooms-ii",
                "difficulty": "MEDIUM",
                "frequency_score": 92.0,
                "acceptance_rate": 0.51,
                "topics": ["Array", "Two Pointers", "Greedy", "Sorting", "Heap (Priority Queue)", "Prefix Sum"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given an array of meeting time intervals intervals where intervals[i] = [starti, endi], return the minimum number of conference rooms required.",
                "starter_code": {"python": "class Solution:\n    def minMeetingRooms(self, intervals: list[list[int]]) -> int:\n        pass\n"},
                "test_cases": [{"input": "intervals = [[0,30],[5,10],[15,20]]", "expected": "2"}]
            },
            {
                "title": "Rate Limiter Simulator",
                "slug": "rate-limiter-simulator",
                "difficulty": "MEDIUM",
                "frequency_score": 90.0,
                "acceptance_rate": 0.58,
                "topics": ["Design", "Hash Table", "Queue"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "Design a sliding window rate limiter that allows up to max_requests per client in a 60-second window.",
                "starter_code": {"python": "class RateLimiter:\n    def __init__(self, max_requests: int):\n        pass\n    def allow(self, client_id: str, timestamp: int) -> bool:\n        return True\n"},
                "test_cases": [{"input": "max_requests = 2, client = \"user1\", timestamps = [1, 20, 45, 62]", "expected": "[true, true, false, true]"}]
            }
        ]
    },

    # BRONZE MINE
    {
        "name": "Swiggy",
        "slug": "swiggy",
        "tier": "bronze",
        "role_title": "Software Development Engineer (Logistics & Delivery)",
        "description": "Campus and fresher recruitment tracks for high-growth consumer tech with real-time routing and state graphs.",
        "logo_icon": "Utensils",
        "community_tips": [
            "Swiggy asks realistic logistics and routing graph problems with real-time tracking nuances."
        ],
        "problems": [
            {
                "title": "Find Peak Element",
                "slug": "find-peak-element",
                "difficulty": "MEDIUM",
                "frequency_score": 90.0,
                "acceptance_rate": 0.46,
                "topics": ["Array", "Binary Search"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "A peak element is an element that is strictly greater than its neighbors. Given a 0-indexed integer array nums, find a peak element, and return its index in O(log n).",
                "starter_code": {"python": "class Solution:\n    def findPeakElement(self, nums: list[int]) -> int:\n        pass\n"},
                "test_cases": [{"input": "nums = [1,2,3,1]", "expected": "2"}]
            },
            {
                "title": "Number of Provinces",
                "slug": "number-of-provinces",
                "difficulty": "MEDIUM",
                "frequency_score": 87.0,
                "acceptance_rate": 0.65,
                "topics": ["Depth-First Search", "Breadth-First Search", "Union Find", "Graph"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "There are n cities. An array isConnected[i][j] = 1 if the ith city and the jth city are directly connected. Return the total number of provinces.",
                "starter_code": {"python": "class Solution:\n    def findCircleNum(self, isConnected: list[list[int]]) -> int:\n        pass\n"},
                "test_cases": [{"input": "isConnected = [[1,1,0],[1,1,0],[0,0,1]]", "expected": "2"}]
            },
            {
                "title": "Container With Most Water",
                "slug": "container-with-most-water",
                "difficulty": "MEDIUM",
                "frequency_score": 85.0,
                "acceptance_rate": 0.54,
                "topics": ["Array", "Two Pointers", "Greedy"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "You are given an integer array height of length n. Find two lines that together with the x-axis form a container, such that the container contains the most water.",
                "starter_code": {"python": "class Solution:\n    def maxArea(self, height: list[int]) -> int:\n        pass\n"},
                "test_cases": [{"input": "height = [1,8,6,2,5,4,8,3,7]", "expected": "49"}]
            }
        ]
    },
    {
        "name": "TCS Digital",
        "slug": "tcs-digital",
        "tier": "bronze",
        "role_title": "Digital Cadre Engineering Associate",
        "description": "Standard Indian campus recruitment assessments with fundamental data structures and algorithmic puzzles.",
        "logo_icon": "Award",
        "community_tips": [
            "TCS Digital online assessments test basic mathematical number theory, dynamic programming, and array manipulation."
        ],
        "problems": [
            {
                "title": "Leaders in an Array",
                "slug": "leaders-in-an-array",
                "difficulty": "EASY",
                "frequency_score": 95.0,
                "acceptance_rate": 0.72,
                "topics": ["Array"],
                "order_index": 1,
                "is_initially_unlocked": True,
                "description": "Given an array arr of positive integers. Your task is to find the leaders in the array. An element of array is leader if it is greater than or equal to all the elements to its right side.",
                "starter_code": {"python": "class Solution:\n    def leaders(self, arr: list[int]) -> list[int]:\n        pass\n"},
                "test_cases": [{"input": "arr = [16, 17, 4, 3, 5, 2]", "expected": "[17, 5, 2]"}]
            },
            {
                "title": "Valid Anagram",
                "slug": "valid-anagram",
                "difficulty": "EASY",
                "frequency_score": 90.0,
                "acceptance_rate": 0.64,
                "topics": ["Hash Table", "String", "Sorting"],
                "order_index": 2,
                "is_initially_unlocked": True,
                "description": "Given two strings s and t, return true if t is an anagram of s, and false otherwise.",
                "starter_code": {"python": "class Solution:\n    def isAnagram(self, s: str, t: str) -> bool:\n        pass\n"},
                "test_cases": [{"input": "s = \"anagram\", t = \"nagaram\"", "expected": "true"}]
            },
            {
                "title": "Climbing Stairs",
                "slug": "climbing-stairs",
                "difficulty": "EASY",
                "frequency_score": 88.0,
                "acceptance_rate": 0.52,
                "topics": ["Math", "Dynamic Programming", "Memoization"],
                "order_index": 3,
                "is_initially_unlocked": True,
                "description": "You are climbing a staircase. It takes n steps to reach the top. Each time you can climb 1 or 2 steps. In how many distinct ways can you climb to the top?",
                "starter_code": {"python": "class Solution:\n    def climbStairs(self, n: int) -> int:\n        pass\n"},
                "test_cases": [{"input": "n = 3", "expected": "3"}]
            }
        ]
    }
]
