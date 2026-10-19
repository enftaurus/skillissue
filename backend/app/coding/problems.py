from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sandbox.runner import TestCase

class CodingProblem(BaseModel):
    id: str
    title: str
    difficulty: str  # 'easy', 'medium', 'hard'
    description: str
    input_format: str
    output_format: str
    constraints: List[str]
    starter_code: Dict[str, str]  # language: code template
    sample_test_cases: List[Dict[str, str]]
    test_cases: List[Dict[str, Any]] = []

CODING_PROBLEMS: Dict[str, CodingProblem] = {
    "two-sum": CodingProblem(
        id="two-sum",
        title="Two Sum — Target Pair Index",
        difficulty="easy",
        description=(
            "Given an array of integers `nums` and an integer `target`, return the 0-indexed positions of the two numbers such that they add up to `target`.\n\n"
            "Assume each input has exactly one solution, and you may not use the same element twice. Output the two indices separated by a space in ascending order."
        ),
        input_format="First line contains integer N (size of array). Second line contains N integers. Third line contains integer target.",
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
    # TODO: Implement O(N) hash map solution
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return seen[complement], i
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
            {"stdin": "3\n3 2 4\n6", "expected_stdout": "1 2"}
        ],
        test_cases=[
            {"stdin": "4\n2 7 11 15\n9", "expected_stdout": "0 1", "is_hidden": False},
            {"stdin": "3\n3 2 4\n6", "expected_stdout": "1 2", "is_hidden": False},
            {"stdin": "2\n3 3\n6", "expected_stdout": "0 1", "is_hidden": True},
            {"stdin": "5\n1 5 7 11 19\n20", "expected_stdout": "0 4", "is_hidden": True}
        ]
    ),
    "merge-intervals": CodingProblem(
        id="merge-intervals",
        title="Merge Intervals — Task Scheduler",
        difficulty="medium",
        description=(
            "Given an array of time intervals where `intervals[i] = [start_i, end_i]`, merge all overlapping intervals, "
            "and return an array of the non-overlapping intervals that cover all the intervals in the input."
        ),
        input_format="First line contains integer N. Next N lines each contain two integers: start and end.",
        output_format="For each merged interval, output: start end on its own line.",
        constraints=[
            "1 <= N <= 10^4",
            "0 <= start_i <= end_i <= 10^5",
            "Target time complexity: O(N log N)"
        ],
        starter_code={
            "python": """import sys

def merge(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        prev = merged[-1]
        if current[0] <= prev[1]:
            prev[1] = max(prev[1], current[1])
        else:
            merged.append(current)
    return merged

if __name__ == '__main__':
    lines = sys.stdin.read().split()
    if lines:
        n = int(lines[0])
        intervals = []
        idx = 1
        for _ in range(n):
            s = int(lines[idx])
            e = int(lines[idx+1])
            intervals.append([s, e])
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

    for (const auto& p : merged) {
        cout << p.first << " " << p.second << endl;
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
        int[][] intervals = new int[n][2];
        for (int i = 0; i < n; i++) {
            intervals[i][0] = sc.nextInt();
            intervals[i][1] = sc.nextInt();
        }

        Arrays.sort(intervals, (a, b) -> Integer.compare(a[0], b[0]));
        List<int[]> merged = new ArrayList<>();
        merged.add(intervals[0]);

        for (int i = 1; i < n; i++) {
            int[] prev = merged.get(merged.size() - 1);
            if (intervals[i][0] <= prev[1]) {
                prev[1] = Math.max(prev[1], intervals[i][1]);
            } else {
                merged.add(intervals[i]);
            }
        }

        for (int[] p : merged) {
            System.out.println(p[0] + " " + p[1]);
        }
    }
}
"""
        },
        sample_test_cases=[
            {"stdin": "4\n1 3\n2 6\n8 10\n15 18", "expected_stdout": "1 6\n8 10\n15 18"},
            {"stdin": "2\n1 4\n4 5", "expected_stdout": "1 5"}
        ],
        test_cases=[
            {"stdin": "4\n1 3\n2 6\n8 10\n15 18", "expected_stdout": "1 6\n8 10\n15 18", "is_hidden": False},
            {"stdin": "2\n1 4\n4 5", "expected_stdout": "1 5", "is_hidden": False},
            {"stdin": "3\n1 4\n0 2\n3 5", "expected_stdout": "0 5", "is_hidden": True}
        ]
    )
}

def get_problem(problem_id: str) -> Optional[CodingProblem]:
    return CODING_PROBLEMS.get(problem_id)

def list_problems() -> List[CodingProblem]:
    return list(CODING_PROBLEMS.values())
