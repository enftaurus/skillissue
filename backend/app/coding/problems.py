from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from backend.app.coding.schemas import CodingProblemPublic

class CodingProblem(BaseModel):
    id: str
    title: str
    difficulty: str  # 'easy', 'medium', 'hard'
    category: str    # 'arrays', 'strings', 'dp', 'graphs', 'trees', 'stack', etc.
    description: str
    input_format: str
    output_format: str
    constraints: List[str]
    starter_code: Dict[str, str]  # language: code template
    sample_test_cases: List[Dict[str, str]]
    test_cases: List[Dict[str, Any]] = []
    ai_coaching_supported: bool = True

    def to_public(self) -> CodingProblemPublic:
        return CodingProblemPublic(
            id=self.id,
            title=self.title,
            difficulty=self.difficulty,
            category=self.category,
            description=self.description,
            input_format=self.input_format,
            output_format=self.output_format,
            constraints=self.constraints,
            starter_code=self.starter_code,
            sample_test_cases=[{"stdin": tc["stdin"], "expected_stdout": tc["expected_stdout"]} for tc in self.sample_test_cases],
            ai_coaching_supported=self.ai_coaching_supported,
        )

CODING_PROBLEMS: Dict[str, CodingProblem] = {
    # 1. Two Sum
    "two-sum": CodingProblem(
        id="two-sum",
        title="Two Sum — Target Pair Index",
        difficulty="easy",
        category="arrays",
        description=(
            "Given an array of integers `nums` and an integer `target`, return the 0-indexed positions of the two numbers such that they add up to `target`.\n\n"
            "Assume each input has exactly one solution, and you may not use the same element twice. Output the two indices separated by a space in ascending order."
        ),
        input_format="First line: integer N. Second line: N space-separated integers. Third line: integer target.",
        output_format="Print two space-separated indices: i j",
        constraints=[
            "2 <= N <= 10^4",
            "-10^9 <= nums[i] <= 10^9",
            "-10^9 <= target <= 10^9",
            "Target time complexity: O(N), Space complexity: O(N)"
        ],
        starter_code={
            "python": 'import sys\n\ndef two_sum(nums, target):\n    # TODO: Implement your solution here\n    # Return two indices (i, j) such that nums[i] + nums[j] == target\n    pass\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        nums = [int(x) for x in lines[1:n+1]]\n        target = int(lines[n+1])\n        res = two_sum(nums, target)\n        if res:\n            i, j = res\n            print(f"{min(i, j)} {max(i, j)}")\n',
            "cpp": '#include <iostream>\n#include <vector>\n#include <algorithm>\n\nusing namespace std;\n\npair<int, int> twoSum(const vector<int>& nums, int target) {\n    // TODO: Implement your solution here\n    return {0, 0};\n}\n\nint main() {\n    int n;\n    if (!(cin >> n)) return 0;\n    vector<int> nums(n);\n    for (int i = 0; i < n; ++i) cin >> nums[i];\n    int target;\n    cin >> target;\n\n    auto res = twoSum(nums, target);\n    cout << min(res.first, res.second) << " " << max(res.first, res.second) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static int[] twoSum(int[] nums, int target) {\n        // TODO: Implement your solution here\n        return new int[]{0, 0};\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int[] nums = new int[n];\n        for (int i = 0; i < n; i++) nums[i] = sc.nextInt();\n        int target = sc.nextInt();\n        int[] res = twoSum(nums, target);\n        System.out.println(Math.min(res[0], res[1]) + " " + Math.max(res[0], res[1]));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "4\n2 7 11 15\n9", "expected_stdout": "0 1"},
            {"stdin": "3\n3 2 4\n6", "expected_stdout": "1 2"},
        ],
        test_cases=[
            {"stdin": "4\n2 7 11 15\n9", "expected_stdout": "0 1", "is_hidden": False},
            {"stdin": "3\n3 2 4\n6", "expected_stdout": "1 2", "is_hidden": False},
            {"stdin": "2\n3 3\n6", "expected_stdout": "0 1", "is_hidden": True},
            {"stdin": "5\n-3 4 3 90 2\n0", "expected_stdout": "0 2", "is_hidden": True},
            {"stdin": "6\n1000000000 5 -1000000000 2 8 10\n0", "expected_stdout": "0 2", "is_hidden": True},
        ]
    ),

    # 2. Valid Parentheses
    "valid-parentheses": CodingProblem(
        id="valid-parentheses",
        title="Valid Parentheses String",
        difficulty="easy",
        category="stack",
        description=(
            "Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\n"
            "An input string is valid if open brackets are closed by the same type of brackets and in the correct order. Output 'true' or 'false'."
        ),
        input_format="A single line containing string s.",
        output_format="Print 'true' if valid, 'false' otherwise.",
        constraints=["1 <= s.length <= 10^5", "s consists of parentheses only '()[]{}'"],
        starter_code={
            "python": 'import sys\n\ndef is_valid(s: str) -> bool:\n    # TODO: Implement your solution here\n    return False\n\nif __name__ == \'__main__\':\n    inp = sys.stdin.read().strip()\n    print("true" if is_valid(inp) else "false")\n',
            "cpp": '#include <iostream>\n#include <string>\n\nusing namespace std;\n\nbool isValid(const string& s) {\n    // TODO: Implement your solution here\n    return false;\n}\n\nint main() {\n    string s;\n    if (cin >> s) {\n        cout << (isValid(s) ? "true" : "false") << endl;\n    }\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static boolean isValid(String s) {\n        // TODO: Implement your solution here\n        return false;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNext()) return;\n        String s = sc.next();\n        System.out.println(isValid(s) ? "true" : "false");\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "()[]{}", "expected_stdout": "true"},
            {"stdin": "(]", "expected_stdout": "false"},
        ],
        test_cases=[
            {"stdin": "()[]{}", "expected_stdout": "true", "is_hidden": False},
            {"stdin": "(]", "expected_stdout": "false", "is_hidden": False},
            {"stdin": "([{}])", "expected_stdout": "true", "is_hidden": True},
            {"stdin": "((((((((", "expected_stdout": "false", "is_hidden": True},
            {"stdin": "()", "expected_stdout": "true", "is_hidden": True},
        ]
    ),

    # 3. Merge Intervals
    "merge-intervals": CodingProblem(
        id="merge-intervals",
        title="Merge Overlapping Intervals",
        difficulty="medium",
        category="arrays",
        description=(
            "Given an array of intervals where intervals[i] = [start_i, end_i], merge all overlapping intervals, and output the resulting intervals sorted by start time."
        ),
        input_format="First line: integer N. Next N lines: two space-separated integers start end.",
        output_format="For each merged interval, print 'start end' on a new line.",
        constraints=["1 <= N <= 10^4", "0 <= start <= end <= 10^5"],
        starter_code={
            "python": 'import sys\n\ndef merge(intervals):\n    # TODO: Implement your solution here\n    return []\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        intervals = []\n        idx = 1\n        for _ in range(n):\n            intervals.append([int(lines[idx]), int(lines[idx+1])])\n            idx += 2\n        res = merge(intervals)\n        for s, e in res:\n            print(f"{s} {e}")\n',
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nvector<pair<int, int>> mergeIntervals(vector<pair<int, int>>& intervals) {\n    // TODO: Implement your solution here\n    return {};\n}\n\nint main() {\n    int n;\n    if (!(cin >> n)) return 0;\n    vector<pair<int, int>> intervals(n);\n    for (int i = 0; i < n; ++i) cin >> intervals[i].first >> intervals[i].second;\n\n    auto res = mergeIntervals(intervals);\n    for (auto& p : res) cout << p.first << " " << p.second << endl;\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static int[][] merge(int[][] intervals) {\n        // TODO: Implement your solution here\n        return new int[0][0];\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int[][] intervals = new int[n][2];\n        for (int i = 0; i < n; i++) {\n            intervals[i][0] = sc.nextInt();\n            intervals[i][1] = sc.nextInt();\n        }\n        int[][] res = merge(intervals);\n        for (int[] p : res) System.out.println(p[0] + " " + p[1]);\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "4\n1 3\n2 6\n8 10\n15 18", "expected_stdout": "1 6\n8 10\n15 18"},
            {"stdin": "2\n1 4\n4 5", "expected_stdout": "1 5"},
        ],
        test_cases=[
            {"stdin": "4\n1 3\n2 6\n8 10\n15 18", "expected_stdout": "1 6\n8 10\n15 18", "is_hidden": False},
            {"stdin": "2\n1 4\n4 5", "expected_stdout": "1 5", "is_hidden": False},
            {"stdin": "1\n1 1", "expected_stdout": "1 1", "is_hidden": True},
            {"stdin": "3\n1 10\n2 3\n4 5", "expected_stdout": "1 10", "is_hidden": True},
        ]
    ),

    # 4. Reverse Linked List
    "reverse-linked-list": CodingProblem(
        id="reverse-linked-list",
        title="Reverse a Singly Linked List",
        difficulty="easy",
        category="linked_lists",
        description=(
            "Given the elements of a singly linked list in order, reverse the list and print the elements in reversed order."
        ),
        input_format="First line: integer N. Second line: N space-separated integers.",
        output_format="Print the reversed elements separated by spaces.",
        constraints=["0 <= N <= 5000", "-5000 <= Node.val <= 5000"],
        starter_code={
            "python": 'import sys\n\ndef reverse_list(values):\n    # TODO: Implement your solution here\n    return []\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        vals = lines[1:n+1]\n        print(" ".join(reverse_list(vals)))\n',
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nvector<int> reverseList(const vector<int>& a) {\n    // TODO: Implement your solution here\n    return {};\n}\n\nint main() {\n    int n;\n    if (!(cin >> n) || n == 0) return 0;\n    vector<int> a(n);\n    for (int i = 0; i < n; ++i) cin >> a[i];\n    auto res = reverseList(a);\n    for (size_t i = 0; i < res.size(); ++i) {\n        cout << res[i] << (i + 1 == res.size() ? "" : " ");\n    }\n    cout << endl;\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static int[] reverseList(int[] a) {\n        // TODO: Implement your solution here\n        return new int[0];\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int[] res = reverseList(a);\n        for (int i = 0; i < res.length; i++) {\n            System.out.print(res[i] + (i + 1 == res.length ? "" : " "));\n        }\n        System.out.println();\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "5\n1 2 3 4 5", "expected_stdout": "5 4 3 2 1"},
            {"stdin": "2\n1 2", "expected_stdout": "2 1"},
        ],
        test_cases=[
            {"stdin": "5\n1 2 3 4 5", "expected_stdout": "5 4 3 2 1", "is_hidden": False},
            {"stdin": "2\n1 2", "expected_stdout": "2 1", "is_hidden": False},
            {"stdin": "1\n42", "expected_stdout": "42", "is_hidden": True},
            {"stdin": "4\n-1 -2 -3 -4", "expected_stdout": "-4 -3 -2 -1", "is_hidden": True},
        ]
    ),

    # 5. Longest Substring Without Repeating Characters
    "longest-substring-without-repeating": CodingProblem(
        id="longest-substring-without-repeating",
        title="Longest Substring Without Repeating Characters",
        difficulty="medium",
        category="strings",
        description=(
            "Given a string `s`, find the length of the longest substring without duplicate characters."
        ),
        input_format="A single line containing string s.",
        output_format="Print an integer denoting the length.",
        constraints=["0 <= s.length <= 5 * 10^4", "s consists of English letters, digits, symbols and spaces"],
        starter_code={
            "python": "import sys\n\ndef length_of_longest_substring(s: str) -> int:\n    # TODO: Implement your solution here\n    return 0\n\nif __name__ == '__main__':\n    line = sys.stdin.readline().rstrip('\\r\\n')\n    print(length_of_longest_substring(line))\n",
            "cpp": '#include <iostream>\n#include <string>\n\nusing namespace std;\n\nint lengthOfLongestSubstring(const string& s) {\n    // TODO: Implement your solution here\n    return 0;\n}\n\nint main() {\n    string s;\n    getline(cin, s);\n    cout << lengthOfLongestSubstring(s) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static int lengthOfLongestSubstring(String s) {\n        // TODO: Implement your solution here\n        return 0;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        String s = sc.hasNextLine() ? sc.nextLine() : "";\n        System.out.println(lengthOfLongestSubstring(s));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "abcabcbb", "expected_stdout": "3"},
            {"stdin": "bbbbb", "expected_stdout": "1"},
        ],
        test_cases=[
            {"stdin": "abcabcbb", "expected_stdout": "3", "is_hidden": False},
            {"stdin": "bbbbb", "expected_stdout": "1", "is_hidden": False},
            {"stdin": "pwwkew", "expected_stdout": "3", "is_hidden": True},
            {"stdin": "au", "expected_stdout": "2", "is_hidden": True},
            {"stdin": "", "expected_stdout": "0", "is_hidden": True},
        ]
    ),

    # 6. Binary Tree Level Order Traversal
    "binary-tree-level-order": CodingProblem(
        id="binary-tree-level-order",
        title="Binary Tree Level Order Traversal",
        difficulty="medium",
        category="trees",
        description=(
            "Given the root of a binary tree as a level-order array (using 'null' for missing nodes), return the level order traversal of its nodes' values (from left to right, level by level).\n\n"
            "Output each level on a new line with space-separated values."
        ),
        input_format="First line: integer N. Second line: N space-separated tokens representing the tree in level-order.",
        output_format="Print each level on a new line with space-separated integers.",
        constraints=["0 <= N <= 2000", "-1000 <= Node.val <= 1000"],
        starter_code={
            "python": 'import sys\n\ndef level_order(tokens):\n    # TODO: Implement your solution here\n    return []\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        tokens = lines[1:n+1]\n        res = level_order(tokens)\n        for lvl in res:\n            print(" ".join(map(str, lvl)))\n',
            "cpp": '#include <iostream>\n#include <vector>\n#include <string>\n\nusing namespace std;\n\nvector<vector<string>> levelOrder(const vector<string>& tokens) {\n    // TODO: Implement your solution here\n    return {};\n}\n\nint main() {\n    int n;\n    if (!(cin >> n) || n == 0) return 0;\n    vector<string> tokens(n);\n    for (int i = 0; i < n; ++i) cin >> tokens[i];\n    auto res = levelOrder(tokens);\n    for (const auto& lvl : res) {\n        for (size_t i = 0; i < lvl.size(); ++i) {\n            cout << lvl[i] << (i + 1 == lvl.size() ? "" : " ");\n        }\n        cout << endl;\n    }\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static List<List<String>> levelOrder(String[] tokens) {\n        // TODO: Implement your solution here\n        return new ArrayList<>();\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        String[] tokens = new String[n];\n        for (int i = 0; i < n; i++) tokens[i] = sc.next();\n        List<List<String>> res = levelOrder(tokens);\n        for (List<String> lvl : res) {\n            System.out.println(String.join(" ", lvl));\n        }\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "5\n3 9 20 null null", "expected_stdout": "3\n9 20"},
        ],
        test_cases=[
            {"stdin": "5\n3 9 20 null null", "expected_stdout": "3\n9 20", "is_hidden": False},
            {"stdin": "1\n1", "expected_stdout": "1", "is_hidden": True},
            {"stdin": "7\n1 2 3 4 5 6 7", "expected_stdout": "1\n2 3\n4 5 6 7", "is_hidden": True},
        ]
    ),

    # 7. Search in Rotated Sorted Array
    "search-in-rotated-sorted-array": CodingProblem(
        id="search-in-rotated-sorted-array",
        title="Search in Rotated Sorted Array",
        difficulty="medium",
        category="binary_search",
        description=(
            "Given an integer array `nums` sorted in ascending order (with distinct values) that was rotated at an unknown pivot index, "
            "and an integer `target`, return the 0-based index of `target` if it is in `nums`, or `-1` if it is not.\n\n"
            "You must write an algorithm with O(log N) runtime complexity."
        ),
        input_format="First line: integer N. Second line: N space-separated integers. Third line: integer target.",
        output_format="Print the index or -1.",
        constraints=["1 <= N <= 10^5", "-10^9 <= nums[i] <= 10^9", "-10^9 <= target <= 10^9"],
        starter_code={
            "python": "import sys\n\ndef search(nums, target):\n    # TODO: Implement your solution here\n    return -1\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        nums = [int(x) for x in lines[1:n+1]]\n        target = int(lines[n+1])\n        print(search(nums, target))\n",
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nint searchRotated(const vector<int>& a, int target) {\n    // TODO: Implement your solution here\n    return -1;\n}\n\nint main() {\n    int n;\n    if (!(cin >> n)) return 0;\n    vector<int> a(n);\n    for (int i = 0; i < n; ++i) cin >> a[i];\n    int target;\n    cin >> target;\n    cout << searchRotated(a, target) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static int search(int[] a, int target) {\n        // TODO: Implement your solution here\n        return -1;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int[] a = new int[n];\n        for (int i = 0; i < n; i++) a[i] = sc.nextInt();\n        int target = sc.nextInt();\n        System.out.println(search(a, target));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "7\n4 5 6 7 0 1 2\n0", "expected_stdout": "4"},
            {"stdin": "7\n4 5 6 7 0 1 2\n3", "expected_stdout": "-1"},
        ],
        test_cases=[
            {"stdin": "7\n4 5 6 7 0 1 2\n0", "expected_stdout": "4", "is_hidden": False},
            {"stdin": "7\n4 5 6 7 0 1 2\n3", "expected_stdout": "-1", "is_hidden": False},
            {"stdin": "1\n1\n0", "expected_stdout": "-1", "is_hidden": True},
            {"stdin": "3\n5 1 3\n5", "expected_stdout": "0", "is_hidden": True},
        ]
    ),

    # 8. Number of Islands
    "number-of-islands": CodingProblem(
        id="number-of-islands",
        title="Number of Islands — Connected Components",
        difficulty="medium",
        category="graphs",
        description=(
            "Given an `m x n` 2D binary grid `grid` which represents a map of '1's (land) and '0's (water), return the number of islands.\n\n"
            "An island is surrounded by water and is formed by connecting adjacent lands horizontally or vertically. You may assume all four edges of the grid are all surrounded by water."
        ),
        input_format="First line: two integers R C. Next R lines: C space-separated characters ('0' or '1').",
        output_format="Print a single integer: total island count.",
        constraints=["1 <= R, C <= 300", "grid[i][j] is '0' or '1'"],
        starter_code={
            "python": "import sys\n\ndef num_islands(grid):\n    # TODO: Implement your solution here\n    return 0\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().split()\n    if lines:\n        r, c = int(lines[0]), int(lines[1])\n        grid = []\n        idx = 2\n        for _ in range(r):\n            grid.append(lines[idx:idx+c])\n            idx += c\n        print(num_islands(grid))\n",
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nint numIslands(vector<vector<char>>& grid) {\n    // TODO: Implement your solution here\n    return 0;\n}\n\nint main() {\n    int r, c;\n    if (!(cin >> r >> c)) return 0;\n    vector<vector<char>> grid(r, vector<char>(c));\n    for (int i = 0; i < r; ++i) {\n        for (int j = 0; j < c; ++j) cin >> grid[i][j];\n    }\n    cout << numIslands(grid) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static int numIslands(char[][] grid) {\n        // TODO: Implement your solution here\n        return 0;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int r = sc.nextInt();\n        int c = sc.nextInt();\n        char[][] grid = new char[r][c];\n        for (int i = 0; i < r; i++) {\n            for (int j = 0; j < c; j++) grid[i][j] = sc.next().charAt(0);\n        }\n        System.out.println(numIslands(grid));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "4 5\n1 1 1 1 0\n1 1 0 1 0\n1 1 0 0 0\n0 0 0 0 0", "expected_stdout": "1"},
            {"stdin": "4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1", "expected_stdout": "3"},
        ],
        test_cases=[
            {"stdin": "4 5\n1 1 1 1 0\n1 1 0 1 0\n1 1 0 0 0\n0 0 0 0 0", "expected_stdout": "1", "is_hidden": False},
            {"stdin": "4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1", "expected_stdout": "3", "is_hidden": False},
            {"stdin": "1 1\n0", "expected_stdout": "0", "is_hidden": True},
            {"stdin": "1 1\n1", "expected_stdout": "1", "is_hidden": True},
        ]
    ),

    # 9. Climbing Stairs
    "climbing-stairs": CodingProblem(
        id="climbing-stairs",
        title="Climbing Stairs",
        difficulty="easy",
        category="dp",
        description=(
            "You are climbing a staircase. It takes `n` steps to reach the top. "
            "Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?"
        ),
        input_format="A single integer n.",
        output_format="Print an integer denoting the number of distinct ways.",
        constraints=["1 <= n <= 45"],
        starter_code={
            "python": "import sys\n\ndef climb_stairs(n: int) -> int:\n    # TODO: Implement your solution here\n    return 0\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().split()\n    if lines:\n        print(climb_stairs(int(lines[0])))\n",
            "cpp": '#include <iostream>\n\nusing namespace std;\n\nint climbStairs(int n) {\n    // TODO: Implement your solution here\n    return 0;\n}\n\nint main() {\n    int n;\n    if (cin >> n) {\n        cout << climbStairs(n) << endl;\n    }\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static int climbStairs(int n) {\n        // TODO: Implement your solution here\n        return 0;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        System.out.println(climbStairs(n));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "2", "expected_stdout": "2"},
            {"stdin": "3", "expected_stdout": "3"},
        ],
        test_cases=[
            {"stdin": "2", "expected_stdout": "2", "is_hidden": False},
            {"stdin": "3", "expected_stdout": "3", "is_hidden": False},
            {"stdin": "1", "expected_stdout": "1", "is_hidden": True},
            {"stdin": "5", "expected_stdout": "8", "is_hidden": True},
            {"stdin": "10", "expected_stdout": "89", "is_hidden": True},
        ]
    ),

    # 10. Coin Change
    "coin-change": CodingProblem(
        id="coin-change",
        title="Coin Change — Fewest Coins",
        difficulty="medium",
        category="dp",
        description=(
            "You are given an integer array `coins` representing coins of different denominations and an integer `amount` "
            "representing a total amount of money.\n\n"
            "Return the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return `-1`."
        ),
        input_format="First line: integer N. Second line: N space-separated coin values. Third line: integer amount.",
        output_format="Print the minimum number of coins, or -1.",
        constraints=["1 <= coins.length <= 12", "1 <= coins[i] <= 2^31 - 1", "0 <= amount <= 10^4"],
        starter_code={
            "python": "import sys\n\ndef coin_change(coins, amount):\n    # TODO: Implement your solution here\n    return -1\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        coins = [int(x) for x in lines[1:n+1]]\n        amount = int(lines[n+1])\n        print(coin_change(coins, amount))\n",
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nint coinChange(const vector<int>& coins, int amount) {\n    // TODO: Implement your solution here\n    return -1;\n}\n\nint main() {\n    int n;\n    if (!(cin >> n)) return 0;\n    vector<int> coins(n);\n    for (int i = 0; i < n; ++i) cin >> coins[i];\n    int amount;\n    cin >> amount;\n    cout << coinChange(coins, amount) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static int coinChange(int[] coins, int amount) {\n        // TODO: Implement your solution here\n        return -1;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int[] coins = new int[n];\n        for (int i = 0; i < n; i++) coins[i] = sc.nextInt();\n        int amount = sc.nextInt();\n        System.out.println(coinChange(coins, amount));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "3\n1 2 5\n11", "expected_stdout": "3"},
            {"stdin": "1\n2\n3", "expected_stdout": "-1"},
        ],
        test_cases=[
            {"stdin": "3\n1 2 5\n11", "expected_stdout": "3", "is_hidden": False},
            {"stdin": "1\n2\n3", "expected_stdout": "-1", "is_hidden": False},
            {"stdin": "1\n1\n0", "expected_stdout": "0", "is_hidden": True},
            {"stdin": "4\n1 5 10 25\n63", "expected_stdout": "6", "is_hidden": True},
        ]
    ),

    # 11. LRU Cache Simulator
    "lru-cache": CodingProblem(
        id="lru-cache",
        title="LRU Cache Operations Simulator",
        difficulty="medium",
        category="design",
        description=(
            "Implement a simulator for a Least Recently Used (LRU) cache with a given capacity.\n\n"
            "Process Q queries: 'get key' (prints value or -1) and 'put key value' (inserts or updates key, evicting the least recently used key if capacity is exceeded)."
        ),
        input_format="First line: integer capacity and integer Q. Next Q lines: operations ('get key' or 'put key value').",
        output_format="For each 'get' query, print the returned value on a new line.",
        constraints=["1 <= capacity <= 3000", "1 <= Q <= 10^4", "0 <= key, value <= 10^5"],
        starter_code={
            "python": "import sys\n\ndef simulate_lru(capacity, queries):\n    # TODO: Implement your LRU Cache simulator here\n    # Return a list of strings representing the output of 'get' queries\n    return []\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().splitlines()\n    if lines:\n        cap, q = map(int, lines[0].split())\n        queries = lines[1:q+1]\n        res = simulate_lru(cap, queries)\n        for r in res:\n            print(r)\n",
            "cpp": '#include <iostream>\n#include <vector>\n#include <string>\n\nusing namespace std;\n\nvoid simulateLRU(int cap, int q) {\n    // TODO: Implement your LRU Cache simulator here\n}\n\nint main() {\n    int cap, q;\n    if (!(cin >> cap >> q)) return 0;\n    simulateLRU(cap, q);\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static void simulateLRU(int cap, int q, Scanner sc) {\n        // TODO: Implement your LRU Cache simulator here\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int cap = sc.nextInt();\n        int q = sc.nextInt();\n        simulateLRU(cap, q, sc);\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "2 6\nput 1 1\nput 2 2\nget 1\nput 3 3\nget 2\nget 3", "expected_stdout": "1\n-1\n3"},
        ],
        test_cases=[
            {"stdin": "2 6\nput 1 1\nput 2 2\nget 1\nput 3 3\nget 2\nget 3", "expected_stdout": "1\n-1\n3", "is_hidden": False},
            {"stdin": "1 3\nput 2 1\nget 2\nget 1", "expected_stdout": "1\n-1", "is_hidden": True},
        ]
    ),

    # 12. Trapping Rain Water
    "trapping-rain-water": CodingProblem(
        id="trapping-rain-water",
        title="Trapping Rain Water",
        difficulty="hard",
        category="arrays",
        description=(
            "Given `n` non-negative integers representing an elevation map where the width of each bar is 1, "
            "compute how much water it can trap after raining."
        ),
        input_format="First line: integer N. Second line: N space-separated non-negative integers.",
        output_format="Print a single integer: total trapped water volume.",
        constraints=["1 <= N <= 2 * 10^4", "0 <= height[i] <= 10^5"],
        starter_code={
            "python": "import sys\n\ndef trap(height):\n    # TODO: Implement your solution here\n    return 0\n\nif __name__ == '__main__':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        h = [int(x) for x in lines[1:n+1]]\n        print(trap(h))\n",
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nlong long trapWater(const vector<int>& h) {\n    // TODO: Implement your solution here\n    return 0;\n}\n\nint main() {\n    int n;\n    if (!(cin >> n)) return 0;\n    vector<int> h(n);\n    for (int i = 0; i < n; ++i) cin >> h[i];\n    cout << trapWater(h) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.Scanner;\n\npublic class Solution {\n    public static long trapWater(int[] h) {\n        // TODO: Implement your solution here\n        return 0;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int[] h = new int[n];\n        for (int i = 0; i < n; i++) h[i] = sc.nextInt();\n        System.out.println(trapWater(h));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "12\n0 1 0 2 1 0 1 3 2 1 2 1", "expected_stdout": "6"},
            {"stdin": "6\n4 2 0 3 2 5", "expected_stdout": "9"},
        ],
        test_cases=[
            {"stdin": "12\n0 1 0 2 1 0 1 3 2 1 2 1", "expected_stdout": "6", "is_hidden": False},
            {"stdin": "6\n4 2 0 3 2 5", "expected_stdout": "9", "is_hidden": False},
            {"stdin": "3\n3 0 3", "expected_stdout": "3", "is_hidden": True},
            {"stdin": "1\n5", "expected_stdout": "0", "is_hidden": True},
        ]
    ),

    # 13. Word Break
    "word-break": CodingProblem(
        id="word-break",
        title="Word Break",
        difficulty="medium",
        category="dp",
        description=(
            "Given a string `s` and a dictionary of strings `wordDict`, return 'true' if `s` can be segmented into a "
            "space-separated sequence of one or more dictionary words, or 'false' otherwise."
        ),
        input_format="First line: string s. Second line: integer M. Third line: M space-separated dictionary words.",
        output_format="Print 'true' or 'false'.",
        constraints=["1 <= s.length <= 300", "1 <= wordDict.length <= 1000", "1 <= wordDict[i].length <= 20"],
        starter_code={
            "python": 'import sys\n\ndef word_break(s, word_set):\n    # TODO: Implement your solution here\n    return False\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        s = lines[0]\n        m = int(lines[1])\n        words = set(lines[2:m+2])\n        print("true" if word_break(s, words) else "false")\n',
            "cpp": '#include <iostream>\n#include <string>\n#include <vector>\n#include <unordered_set>\n\nusing namespace std;\n\nbool wordBreak(const string& s, const unordered_set<string>& dict) {\n    // TODO: Implement your solution here\n    return false;\n}\n\nint main() {\n    string s;\n    if (!(cin >> s)) return 0;\n    int m;\n    cin >> m;\n    unordered_set<string> dict;\n    for (int i = 0; i < m; ++i) {\n        string w; cin >> w;\n        dict.insert(w);\n    }\n    cout << (wordBreak(s, dict) ? "true" : "false") << endl;\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static boolean wordBreak(String s, Set<String> dict) {\n        // TODO: Implement your solution here\n        return false;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNext()) return;\n        String s = sc.next();\n        int m = sc.nextInt();\n        HashSet<String> dict = new HashSet<>();\n        for (int i = 0; i < m; i++) dict.add(sc.next());\n        System.out.println(wordBreak(s, dict) ? "true" : "false");\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "leetcode\n2\nleet code", "expected_stdout": "true"},
            {"stdin": "catsandog\n5\ncats dog sand and cat", "expected_stdout": "false"},
        ],
        test_cases=[
            {"stdin": "leetcode\n2\nleet code", "expected_stdout": "true", "is_hidden": False},
            {"stdin": "catsandog\n5\ncats dog sand and cat", "expected_stdout": "false", "is_hidden": False},
            {"stdin": "applepenapple\n2\napple pen", "expected_stdout": "true", "is_hidden": True},
        ]
    ),

    # 14. Course Schedule (Detect Cycle in Directed Graph)
    "course-schedule": CodingProblem(
        id="course-schedule",
        title="Course Schedule — Dependency Resolution",
        difficulty="medium",
        category="graphs",
        description=(
            "There are a total of `numCourses` courses you have to take, labeled from 0 to `numCourses - 1`.\n\n"
            "You are given prerequisites pairs [a, b] indicating that you must take course b before taking course a. "
            "Determine if it is possible to finish all courses (i.e., graph has no directed cycle). Print 'true' or 'false'."
        ),
        input_format="First line: integer numCourses and integer P (number of prerequisites). Next P lines: two integers a b.",
        output_format="Print 'true' if possible, 'false' otherwise.",
        constraints=["1 <= numCourses <= 2000", "0 <= P <= 5000"],
        starter_code={
            "python": 'import sys\n\ndef can_finish(n, prereqs):\n    # TODO: Implement your solution here\n    return False\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        n = int(lines[0])\n        p = int(lines[1])\n        prereqs = []\n        idx = 2\n        for _ in range(p):\n            prereqs.append([int(lines[idx]), int(lines[idx+1])])\n            idx += 2\n        print("true" if can_finish(n, prereqs) else "false")\n',
            "cpp": '#include <iostream>\n#include <vector>\n\nusing namespace std;\n\nbool canFinish(int n, const vector<pair<int, int>>& prereqs) {\n    // TODO: Implement your solution here\n    return false;\n}\n\nint main() {\n    int n, p;\n    if (!(cin >> n >> p)) return 0;\n    vector<pair<int, int>> prereqs(p);\n    for (int i = 0; i < p; ++i) cin >> prereqs[i].first >> prereqs[i].second;\n    cout << (canFinish(n, prereqs) ? "true" : "false") << endl;\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static boolean canFinish(int n, int[][] prereqs) {\n        // TODO: Implement your solution here\n        return false;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int n = sc.nextInt();\n        int p = sc.nextInt();\n        int[][] prereqs = new int[p][2];\n        for (int i = 0; i < p; i++) {\n            prereqs[i][0] = sc.nextInt();\n            prereqs[i][1] = sc.nextInt();\n        }\n        System.out.println(canFinish(n, prereqs) ? "true" : "false");\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "2 1\n1 0", "expected_stdout": "true"},
            {"stdin": "2 2\n1 0\n0 1", "expected_stdout": "false"},
        ],
        test_cases=[
            {"stdin": "2 1\n1 0", "expected_stdout": "true", "is_hidden": False},
            {"stdin": "2 2\n1 0\n0 1", "expected_stdout": "false", "is_hidden": False},
            {"stdin": "3 2\n1 0\n2 1", "expected_stdout": "true", "is_hidden": True},
        ]
    ),

    # 15. Median of Two Sorted Arrays
    "median-of-two-sorted-arrays": CodingProblem(
        id="median-of-two-sorted-arrays",
        title="Median of Two Sorted Arrays",
        difficulty="hard",
        category="binary_search",
        description=(
            "Given two sorted arrays `nums1` and `nums2` of size `m` and `n` respectively, return the median of the two sorted arrays.\n\n"
            "Format the output as a floating-point number with exactly 1 decimal place (or integer format if whole, e.g. 2.0 or 2.5)."
        ),
        input_format="First line: integer M. Second line: M space-separated integers. Third line: integer N. Fourth line: N space-separated integers.",
        output_format="Print the median (e.g. 2.0 or 2.5).",
        constraints=["0 <= M, N <= 1000", "1 <= M + N <= 2000", "-10^6 <= nums1[i], nums2[i] <= 10^6"],
        starter_code={
            "python": 'import sys\n\ndef find_median_sorted_arrays(nums1, nums2):\n    # TODO: Implement your solution here\n    return 0.0\n\nif __name__ == \'__main__\':\n    lines = sys.stdin.read().split()\n    if lines:\n        m = int(lines[0])\n        nums1 = [int(x) for x in lines[1:m+1]]\n        idx = m + 1\n        n = int(lines[idx])\n        nums2 = [int(x) for x in lines[idx+1:idx+1+n]]\n        med = find_median_sorted_arrays(nums1, nums2)\n        print(f"{med:.1f}")\n',
            "cpp": '#include <iostream>\n#include <vector>\n#include <iomanip>\n\nusing namespace std;\n\ndouble findMedianSortedArrays(const vector<int>& a, const vector<int>& b) {\n    // TODO: Implement your solution here\n    return 0.0;\n}\n\nint main() {\n    int m;\n    if (!(cin >> m)) return 0;\n    vector<int> a(m);\n    for (int i = 0; i < m; ++i) cin >> a[i];\n    int n;\n    cin >> n;\n    vector<int> b(n);\n    for (int i = 0; i < n; ++i) cin >> b[i];\n\n    cout << fixed << setprecision(1) << findMedianSortedArrays(a, b) << endl;\n    return 0;\n}\n',
            "java": 'import java.util.*;\n\npublic class Solution {\n    public static double findMedianSortedArrays(int[] a, int[] b) {\n        // TODO: Implement your solution here\n        return 0.0;\n    }\n\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (!sc.hasNextInt()) return;\n        int m = sc.nextInt();\n        int[] a = new int[m];\n        for (int i = 0; i < m; i++) a[i] = sc.nextInt();\n        int n = sc.nextInt();\n        int[] b = new int[n];\n        for (int i = 0; i < n; i++) b[i] = sc.nextInt();\n        System.out.printf(Locale.US, "%.1f\\n", findMedianSortedArrays(a, b));\n    }\n}\n'
        },
        sample_test_cases=[
            {"stdin": "2\n1 3\n1\n2", "expected_stdout": "2.0"},
            {"stdin": "2\n1 2\n2\n3 4", "expected_stdout": "2.5"},
        ],
        test_cases=[
            {"stdin": "2\n1 3\n1\n2", "expected_stdout": "2.0", "is_hidden": False},
            {"stdin": "2\n1 2\n2\n3 4", "expected_stdout": "2.5", "is_hidden": False},
            {"stdin": "1\n0\n1\n0", "expected_stdout": "0.0", "is_hidden": True},
        ]
    ),
}

def list_problems() -> List[CodingProblem]:
    return list(CODING_PROBLEMS.values())

def get_problem(problem_id: str) -> Optional[CodingProblem]:
    if problem_id in CODING_PROBLEMS:
        return CODING_PROBLEMS[problem_id]
    if problem_id.lower().startswith("cf-"):
        from backend.app.coding.codeforces import CodeforcesClient
        return CodeforcesClient.get_coding_problem_by_id(problem_id)
    return None
