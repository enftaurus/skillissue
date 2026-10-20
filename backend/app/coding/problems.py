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
            "python": """import sys

def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return seen[diff], i
        seen[num] = i
    return 0, 0

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        nums = [int(x) for x in lines[1:n+1]]
        target = int(lines[n+1])
        i, j = two_sum(nums, target)
        print(f"{min(i, j)} {max(i, j)}")
""",
            "cpp": """#include <iostream>
#include <vector>
#include <unordered_map>
#include <algorithm>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<int> nums(n);
    for (int i = 0; i < n; ++i) cin >> nums[i];
    int target;
    cin >> target;

    unordered_map<int, int> seen;
    for (int i = 0; i < n; ++i) {
        int comp = target - nums[i];
        if (seen.find(comp) != seen.end()) {
            cout << seen[comp] << " " << i << endl;
            return 0;
        }
        seen[nums[i]] = i;
    }
    return 0;
}
""",
            "java": """import java.util.Scanner;
import java.util.HashMap;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[] nums = new int[n];
        for (int i = 0; i < n; i++) nums[i] = sc.nextInt();
        int target = sc.nextInt();

        HashMap<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < n; i++) {
            int comp = target - nums[i];
            if (map.containsKey(comp)) {
                System.out.println(map.get(comp) + " " + i);
                return;
            }
            map.put(nums[i], i);
        }
    }
}
"""
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
            "python": """import sys

def is_valid(s: str) -> bool:
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for char in s.strip():
        if char in mapping:
            top = stack.pop() if stack else '#'
            if mapping[char] != top:
                return False
        else:
            stack.append(char)
    return len(stack) == 0

if __name__ == '__main__':
    inp = sys.stdin.read().strip()
    print("true" if is_valid(inp) else "false")
""",
            "cpp": """#include <iostream>
#include <string>
#include <stack>

using namespace std;

bool isValid(const string& s) {
    stack<char> st;
    for (char c : s) {
        if (c == '(' || c == '{' || c == '[') st.push(c);
        else {
            if (st.empty()) return false;
            char top = st.top(); st.pop();
            if (c == ')' && top != '(') return false;
            if (c == '}' && top != '{') return false;
            if (c == ']' && top != '[') return false;
        }
    }
    return st.empty();
}

int main() {
    string s;
    if (cin >> s) {
        cout << (isValid(s) ? "true" : "false") << endl;
    }
    return 0;
}
""",
            "java": """import java.util.Scanner;
import java.util.Stack;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNext()) return;
        String s = sc.next();
        Stack<Character> stack = new Stack<>();
        boolean ok = true;
        for (char c : s.toCharArray()) {
            if (c == '(' || c == '{' || c == '[') {
                stack.push(c);
            } else {
                if (stack.isEmpty()) { ok = false; break; }
                char top = stack.pop();
                if (c == ')' && top != '(') { ok = false; break; }
                if (c == '}' && top != '{') { ok = false; break; }
                if (c == ']' && top != '[') { ok = false; break; }
            }
        }
        System.out.println((ok && stack.isEmpty()) ? "true" : "false");
    }
}
"""
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
            "python": """import sys

def merge(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for cur in intervals[1:]:
        prev = merged[-1]
        if cur[0] <= prev[1]:
            prev[1] = max(prev[1], cur[1])
        else:
            merged.append(cur)
    return merged

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        intervals = []
        idx = 1
        for _ in range(n):
            intervals.append([int(lines[idx]), int(lines[idx+1])])
            idx += 2
        res = merge(intervals)
        for s, e in res:
            print(f"{s} {e}")
""",
            "cpp": """#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<pair<int, int>> intervals(n);
    for (int i = 0; i < n; ++i) cin >> intervals[i].first >> intervals[i].second;

    sort(intervals.begin(), intervals.end());
    vector<pair<int, int>> merged;
    merged.push_back(intervals[0]);

    for (size_t i = 1; i < intervals.size(); ++i) {
        if (intervals[i].first <= merged.back().second) {
            merged.back().second = max(merged.back().second, intervals[i].second);
        } else {
            merged.push_back(intervals[i]);
        }
    }

    for (auto& p : merged) cout << p.first << " " << p.second << endl;
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[][] intervals = new int[n][2];
        for (int i = 0; i < n; i++) {
            intervals[i][0] = sc.nextInt();
            intervals[i][1] = sc.nextInt();
        }
        Arrays.sort(intervals, (a, b) -> Integer.compare(a[0], b[0]));
        List<int[]> res = new ArrayList<>();
        res.add(intervals[0]);
        for (int i = 1; i < n; i++) {
            int[] prev = res.get(res.size() - 1);
            if (intervals[i][0] <= prev[1]) {
                prev[1] = Math.max(prev[1], intervals[i][1]);
            } else {
                res.add(intervals[i]);
            }
        }
        for (int[] p : res) System.out.println(p[0] + " " + p[1]);
    }
}
"""
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
            "python": """import sys

def reverse_list(values):
    return values[::-1]

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        vals = lines[1:n+1]
        print(" ".join(reverse_list(vals)))
""",
            "cpp": """#include <iostream>
#include <vector>

using namespace std;

int main() {
    int n;
    if (!(cin >> n) || n == 0) return 0;
    vector<int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];
    for (int i = n - 1; i >= 0; --i) {
        cout << a[i] << (i == 0 ? "" : " ");
    }
    cout << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextInt();
        for (int i = n - 1; i >= 0; i--) {
            System.out.print(a[i] + (i == 0 ? "" : " "));
        }
        System.out.println();
    }
}
"""
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
            "python": """import sys

def length_of_longest_substring(s: str) -> int:
    char_map = {}
    max_len = 0
    left = 0
    for right, char in enumerate(s):
        if char in char_map and char_map[char] >= left:
            left = char_map[char] + 1
        char_map[char] = right
        max_len = max(max_len, right - left + 1)
    return max_len

if __name__ == '__main__':
    line = sys.stdin.readline().rstrip('\\r\\n')
    print(length_of_longest_substring(line))
""",
            "cpp": """#include <iostream>
#include <string>
#include <unordered_map>
#include <algorithm>

using namespace std;

int main() {
    string s;
    getline(cin, s);
    unordered_map<char, int> seen;
    int max_len = 0, left = 0;
    for (int right = 0; right < (int)s.size(); ++right) {
        if (seen.count(s[right]) && seen[s[right]] >= left) {
            left = seen[s[right]] + 1;
        }
        seen[s[right]] = right;
        max_len = max(max_len, right - left + 1);
    }
    cout << max_len << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;
import java.util.HashMap;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String s = sc.hasNextLine() ? sc.nextLine() : "";
        HashMap<Character, Integer> seen = new HashMap<>();
        int maxLen = 0, left = 0;
        for (int right = 0; right < s.length(); right++) {
            char c = s.charAt(right);
            if (seen.containsKey(c) && seen.get(c) >= left) {
                left = seen.get(c) + 1;
            }
            seen.put(c, right);
            maxLen = Math.max(maxLen, right - left + 1);
        }
        System.out.println(maxLen);
    }
}
"""
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
            "python": """import sys
from collections import deque

def level_order(tokens):
    if not tokens or tokens[0] == "null":
        return []
    # Build tree from level-order tokens
    nodes = [None if t == "null" else int(t) for t in tokens]
    levels = []
    level = [0]
    while level:
        levels.append([nodes[i] for i in level if i < len(nodes) and nodes[i] is not None])
        next_level = []
        for i in level:
            left = 2 * i + 1
            right = 2 * i + 2
            if left < len(nodes) and nodes[left] is not None:
                next_level.append(left)
            if right < len(nodes) and nodes[right] is not None:
                next_level.append(right)
        level = next_level
    return [l for l in levels if l]

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        tokens = lines[1:n+1]
        res = level_order(tokens)
        for lvl in res:
            print(" ".join(map(str, lvl)))
""",
            "cpp": """#include <iostream>
#include <vector>
#include <string>
#include <queue>

using namespace std;

int main() {
    int n;
    if (!(cin >> n) || n == 0) return 0;
    vector<string> tokens(n);
    for (int i = 0; i < n; ++i) cin >> tokens[i];
    if (tokens[0] == "null") return 0;

    queue<int> q;
    q.push(0);
    while (!q.empty()) {
        int sz = q.size();
        bool first = true;
        for (int i = 0; i < sz; ++i) {
            int idx = q.front(); q.pop();
            if (idx < n && tokens[idx] != "null") {
                if (!first) cout << " ";
                cout << tokens[idx];
                first = false;
                int left = 2 * idx + 1;
                int right = 2 * idx + 2;
                if (left < n && tokens[left] != "null") q.push(left);
                if (right < n && tokens[right] != "null") q.push(right);
            }
        }
        cout << endl;
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        String[] tokens = new String[n];
        for (int i = 0; i < n; i++) tokens[i] = sc.next();
        if (n == 0 || tokens[0].equals("null")) return;

        Queue<Integer> q = new LinkedList<>();
        q.add(0);
        while (!q.isEmpty()) {
            int sz = q.size();
            List<String> cur = new ArrayList<>();
            for (int i = 0; i < sz; i++) {
                int idx = q.poll();
                if (idx < n && !tokens[idx].equals("null")) {
                    cur.add(tokens[idx]);
                    int left = 2 * idx + 1;
                    int right = 2 * idx + 2;
                    if (left < n && !tokens[left].equals("null")) q.add(left);
                    if (right < n && !tokens[right].equals("null")) q.add(right);
                }
            }
            if (!cur.isEmpty()) {
                System.out.println(String.join(" ", cur));
            }
        }
    }
}
"""
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
            "python": """import sys

def search(nums, target):
    low, high = 0, len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        if nums[mid] == target:
            return mid
        if nums[low] <= nums[mid]:
            if nums[low] <= target < nums[mid]:
                high = mid - 1
            else:
                low = mid + 1
        else:
            if nums[mid] < target <= nums[high]:
                low = mid + 1
            else:
                high = mid - 1
    return -1

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        nums = [int(x) for x in lines[1:n+1]]
        target = int(lines[n+1])
        print(search(nums, target))
""",
            "cpp": """#include <iostream>
#include <vector>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];
    int target;
    cin >> target;

    int l = 0, r = n - 1, ans = -1;
    while (l <= r) {
        int mid = l + (r - l) / 2;
        if (a[mid] == target) { ans = mid; break; }
        if (a[l] <= a[mid]) {
            if (a[l] <= target && target < a[mid]) r = mid - 1;
            else l = mid + 1;
        } else {
            if (a[mid] < target && target <= a[r]) l = mid + 1;
            else r = mid - 1;
        }
    }
    cout << ans << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextInt();
        int target = sc.nextInt();

        int l = 0, r = n - 1, ans = -1;
        while (l <= r) {
            int mid = l + (r - l) / 2;
            if (a[mid] == target) { ans = mid; break; }
            if (a[l] <= a[mid]) {
                if (a[l] <= target && target < a[mid]) r = mid - 1;
                else l = mid + 1;
            } else {
                if (a[mid] < target && target <= a[r]) l = mid + 1;
                else r = mid - 1;
            }
        }
        System.out.println(ans);
    }
}
"""
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
            "python": """import sys

def num_islands(grid):
    if not grid:
        return 0
    r, c = len(grid), len(grid[0])
    count = 0

    def dfs(i, j):
        if i < 0 or i >= r or j < 0 or j >= c or grid[i][j] != '1':
            return
        grid[i][j] = '0'
        dfs(i+1, j)
        dfs(i-1, j)
        dfs(i, j+1)
        dfs(i, j-1)

    for i in range(r):
        for j in range(c):
            if grid[i][j] == '1':
                count += 1
                dfs(i, j)
    return count

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        r, c = int(lines[0]), int(lines[1])
        grid = []
        idx = 2
        for _ in range(r):
            grid.append(lines[idx:idx+c])
            idx += c
        print(num_islands(grid))
""",
            "cpp": """#include <iostream>
#include <vector>

using namespace std;

void dfs(vector<vector<char>>& grid, int i, int j, int r, int c) {
    if (i < 0 || i >= r || j < 0 || j >= c || grid[i][j] != '1') return;
    grid[i][j] = '0';
    dfs(grid, i + 1, j, r, c);
    dfs(grid, i - 1, j, r, c);
    dfs(grid, i, j + 1, r, c);
    dfs(grid, i, j - 1, r, c);
}

int main() {
    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<vector<char>> grid(r, vector<char>(c));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) cin >> grid[i][j];
    }
    int count = 0;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '1') {
                count++;
                dfs(grid, i, j, r, c);
            }
        }
    }
    cout << count << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;

public class Solution {
    static void dfs(char[][] grid, int i, int j, int r, int c) {
        if (i < 0 || i >= r || j < 0 || j >= c || grid[i][j] != '1') return;
        grid[i][j] = '0';
        dfs(grid, i + 1, j, r, c);
        dfs(grid, i - 1, j, r, c);
        dfs(grid, i, j + 1, r, c);
        dfs(grid, i, j - 1, r, c);
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int r = sc.nextInt();
        int c = sc.nextInt();
        char[][] grid = new char[r][c];
        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) grid[i][j] = sc.next().charAt(0);
        }
        int count = 0;
        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                if (grid[i][j] == '1') {
                    count++;
                    dfs(grid, i, j, r, c);
                }
            }
        }
        System.out.println(count);
    }
}
"""
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
            "python": """import sys

def climb_stairs(n: int) -> int:
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        print(climb_stairs(int(lines[0])))
""",
            "cpp": """#include <iostream>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    if (n <= 2) { cout << n << endl; return 0; }
    int a = 1, b = 2;
    for (int i = 3; i <= n; ++i) {
        int c = a + b;
        a = b;
        b = c;
    }
    cout << b << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        if (n <= 2) { System.out.println(n); return; }
        int a = 1, b = 2;
        for (int i = 3; i <= n; i++) {
            int c = a + b;
            a = b;
            b = c;
        }
        System.out.println(b);
    }
}
"""
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
            "python": """import sys

def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for x in range(coin, amount + 1):
            dp[x] = min(dp[x], dp[x - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        coins = [int(x) for x in lines[1:n+1]]
        amount = int(lines[n+1])
        print(coin_change(coins, amount))
""",
            "cpp": """#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<int> coins(n);
    for (int i = 0; i < n; ++i) cin >> coins[i];
    int amount;
    cin >> amount;

    vector<int> dp(amount + 1, 1e9);
    dp[0] = 0;
    for (int c : coins) {
        for (int x = c; x <= amount; ++x) {
            dp[x] = min(dp[x], dp[x - c] + 1);
        }
    }
    cout << (dp[amount] >= 1e9 ? -1 : dp[amount]) << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;
import java.util.Arrays;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[] coins = new int[n];
        for (int i = 0; i < n; i++) coins[i] = sc.nextInt();
        int amount = sc.nextInt();

        int[] dp = new int[amount + 1];
        Arrays.fill(dp, 1000000);
        dp[0] = 0;
        for (int c : coins) {
            for (int x = c; x <= amount; x++) {
                dp[x] = Math.min(dp[x], dp[x - c] + 1);
            }
        }
        System.out.println(dp[amount] >= 1000000 ? -1 : dp[amount]);
    }
}
"""
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
            "python": """import sys
from collections import OrderedDict

def simulate_lru(capacity, queries):
    cache = OrderedDict()
    results = []
    for q in queries:
        parts = q.split()
        if parts[0] == "get":
            k = int(parts[1])
            if k in cache:
                cache.move_to_end(k)
                results.append(str(cache[k]))
            else:
                results.append("-1")
        elif parts[0] == "put":
            k, v = int(parts[1]), int(parts[2])
            if k in cache:
                cache.move_to_end(k)
            cache[k] = v
            if len(cache) > capacity:
                cache.popitem(last=False)
    return results

if __name__ == '__main__':
    lines = sys.stdin.read().splitlines()
    if lines:
        cap, q = map(int, lines[0].split())
        queries = lines[1:q+1]
        res = simulate_lru(cap, queries)
        for r in res:
            print(r)
""",
            "cpp": """#include <iostream>
#include <unordered_map>
#include <list>
#include <string>

using namespace std;

int main() {
    int cap, q;
    if (!(cin >> cap >> q)) return 0;
    list<pair<int, int>> lru;
    unordered_map<int, list<pair<int, int>>::iterator> mp;

    for (int i = 0; i < q; ++i) {
        string op;
        cin >> op;
        if (op == "get") {
            int k; cin >> k;
            if (mp.count(k)) {
                auto it = mp[k];
                int val = it->second;
                lru.erase(it);
                lru.push_front({k, val});
                mp[k] = lru.begin();
                cout << val << endl;
            } else {
                cout << -1 << endl;
            }
        } else if (op == "put") {
            int k, v; cin >> k >> v;
            if (mp.count(k)) {
                lru.erase(mp[k]);
            } else if ((int)lru.size() == cap) {
                mp.erase(lru.back().first);
                lru.pop_back();
            }
            lru.push_front({k, v});
            mp[k] = lru.begin();
        }
    }
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int cap = sc.nextInt();
        int q = sc.nextInt();

        LinkedHashMap<Integer, Integer> map = new LinkedHashMap<>(cap, 0.75f, true) {
            protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) {
                return size() > cap;
            }
        };

        for (int i = 0; i < q; i++) {
            String op = sc.next();
            if (op.equals("get")) {
                int k = sc.nextInt();
                System.out.println(map.getOrDefault(k, -1));
            } else if (op.equals("put")) {
                int k = sc.nextInt();
                int v = sc.nextInt();
                map.put(k, v);
            }
        }
    }
}
"""
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
            "python": """import sys

def trap(height):
    if not height:
        return 0
    left, right = 0, len(height) - 1
    left_max, right_max = 0, 0
    water = 0
    while left < right:
        if height[left] < height[right]:
            if height[left] >= left_max:
                left_max = height[left]
            else:
                water += left_max - height[left]
            left += 1
        else:
            if height[right] >= right_max:
                right_max = height[right]
            else:
                water += right_max - height[right]
            right -= 1
    return water

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        h = [int(x) for x in lines[1:n+1]]
        print(trap(h))
""",
            "cpp": """#include <iostream>
#include <vector>

using namespace std;

int main() {
    int n;
    if (!(cin >> n)) return 0;
    vector<int> h(n);
    for (int i = 0; i < n; ++i) cin >> h[i];

    int l = 0, r = n - 1;
    int l_max = 0, r_max = 0;
    long long water = 0;
    while (l < r) {
        if (h[l] < h[r]) {
            if (h[l] >= l_max) l_max = h[l];
            else water += l_max - h[l];
            l++;
        } else {
            if (h[r] >= r_max) r_max = h[r];
            else water += r_max - h[r];
            r--;
        }
    }
    cout << water << endl;
    return 0;
}
""",
            "java": """import java.util.Scanner;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int[] h = new int[n];
        for (int i = 0; i < n; i++) h[i] = sc.nextInt();

        int l = 0, r = n - 1;
        int lMax = 0, rMax = 0;
        long water = 0;
        while (l < r) {
            if (h[l] < h[r]) {
                if (h[l] >= lMax) lMax = h[l];
                else water += lMax - h[l];
                l++;
            } else {
                if (h[r] >= rMax) rMax = h[r];
                else water += rMax - h[r];
                r--;
            }
        }
        System.out.println(water);
    }
}
"""
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
            "python": """import sys

def word_break(s, word_set):
    dp = [False] * (len(s) + 1)
    dp[0] = True
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in word_set:
                dp[i] = True
                break
    return dp[len(s)]

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        s = lines[0]
        m = int(lines[1])
        words = set(lines[2:m+2])
        print("true" if word_break(s, words) else "false")
""",
            "cpp": """#include <iostream>
#include <string>
#include <vector>
#include <unordered_set>

using namespace std;

int main() {
    string s;
    if (!(cin >> s)) return 0;
    int m;
    cin >> m;
    unordered_set<string> dict;
    for (int i = 0; i < m; ++i) {
        string w; cin >> w;
        dict.insert(w);
    }
    int n = s.size();
    vector<bool> dp(n + 1, false);
    dp[0] = true;
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < i; ++j) {
            if (dp[j] && dict.count(s.substr(j, i - j))) {
                dp[i] = true;
                break;
            }
        }
    }
    cout << (dp[n] ? "true" : "false") << endl;
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNext()) return;
        String s = sc.next();
        int m = sc.nextInt();
        HashSet<String> dict = new HashSet<>();
        for (int i = 0; i < m; i++) dict.add(sc.next());

        int n = s.length();
        boolean[] dp = new boolean[n + 1];
        dp[0] = true;
        for (int i = 1; i <= n; i++) {
            for (int j = 0; j < i; j++) {
                if (dp[j] && dict.contains(s.substring(j, i))) {
                    dp[i] = true;
                    break;
                }
            }
        }
        System.out.println(dp[n] ? "true" : "false");
    }
}
"""
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
            "python": """import sys
from collections import deque, defaultdict

def can_finish(n, prereqs):
    graph = defaultdict(list)
    indegree = [0] * n
    for dest, src in prereqs:
        graph[src].append(dest)
        indegree[dest] += 1
    q = deque([i for i in range(n) if indegree[i] == 0])
    taken = 0
    while q:
        node = q.popleft()
        taken += 1
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                q.append(neighbor)
    return taken == n

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        p = int(lines[1])
        prereqs = []
        idx = 2
        for _ in range(p):
            prereqs.append((int(lines[idx]), int(lines[idx+1])))
            idx += 2
        print("true" if can_finish(n, prereqs) else "false")
""",
            "cpp": """#include <iostream>
#include <vector>
#include <queue>

using namespace std;

int main() {
    int n, p;
    if (!(cin >> n >> p)) return 0;
    vector<vector<int>> g(n);
    vector<int> indeg(n, 0);
    for (int i = 0; i < p; ++i) {
        int a, b; cin >> a >> b;
        g[b].push_back(a);
        indeg[a]++;
    }
    queue<int> q;
    for (int i = 0; i < n; ++i) if (indeg[i] == 0) q.push(i);
    int taken = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        taken++;
        for (int v : g[u]) {
            if (--indeg[v] == 0) q.push(v);
        }
    }
    cout << (taken == n ? "true" : "false") << endl;
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int n = sc.nextInt();
        int p = sc.nextInt();
        List<List<Integer>> g = new ArrayList<>();
        for (int i = 0; i < n; i++) g.add(new ArrayList<>());
        int[] indeg = new int[n];
        for (int i = 0; i < p; i++) {
            int a = sc.nextInt();
            int b = sc.nextInt();
            g.get(b).add(a);
            indeg[a]++;
        }
        Queue<Integer> q = new LinkedList<>();
        for (int i = 0; i < n; i++) if (indeg[i] == 0) q.add(i);
        int taken = 0;
        while (!q.isEmpty()) {
            int u = q.poll();
            taken++;
            for (int v : g.get(u)) {
                if (--indeg[v] == 0) q.add(v);
            }
        }
        System.out.println(taken == n ? "true" : "false");
    }
}
"""
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
            "python": """import sys

def find_median_sorted_arrays(nums1, nums2):
    merged = sorted(nums1 + nums2)
    l = len(merged)
    if l % 2 == 1:
        return float(merged[l // 2])
    return (merged[l // 2 - 1] + merged[l // 2]) / 2.0

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        m = int(lines[0])
        nums1 = [int(x) for x in lines[1:m+1]]
        idx = m + 1
        n = int(lines[idx])
        nums2 = [int(x) for x in lines[idx+1:idx+1+n]]
        med = find_median_sorted_arrays(nums1, nums2)
        print(f"{med:.1f}")
""",
            "cpp": """#include <iostream>
#include <vector>
#include <algorithm>
#include <iomanip>

using namespace std;

int main() {
    int m;
    if (!(cin >> m)) return 0;
    vector<int> a(m);
    for (int i = 0; i < m; ++i) cin >> a[i];
    int n;
    cin >> n;
    vector<int> b(n);
    for (int i = 0; i < n; ++i) cin >> b[i];

    vector<int> c;
    c.insert(c.end(), a.begin(), a.end());
    c.insert(c.end(), b.begin(), b.end());
    sort(c.begin(), c.end());

    int sz = c.size();
    double med = (sz % 2 == 1) ? c[sz / 2] : (c[sz / 2 - 1] + c[sz / 2]) / 2.0;
    cout << fixed << setprecision(1) << med << endl;
    return 0;
}
""",
            "java": """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNextInt()) return;
        int m = sc.nextInt();
        List<Integer> list = new ArrayList<>();
        for (int i = 0; i < m; i++) list.add(sc.nextInt());
        int n = sc.nextInt();
        for (int i = 0; i < n; i++) list.add(sc.nextInt());
        Collections.sort(list);
        int sz = list.size();
        double med = (sz % 2 == 1) ? list.get(sz / 2) : (list.get(sz / 2 - 1) + list.get(sz / 2)) / 2.0;
        System.out.printf(Locale.US, "%.1f\\n", med);
    }
}
"""
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
    return CODING_PROBLEMS.get(problem_id)
