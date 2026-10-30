import time
import random
import string
import hashlib
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger

TAG_MAPPING = {
    "dynamic programming": "dp",
    "dp": "dp",
    "graphs": "graphs",
    "graph": "graphs",
    "trees": "trees",
    "tree": "trees",
    "greedy": "greedy",
    "strings": "strings",
    "string": "strings",
    "binary search": "binary search",
    "math": "math",
    "mathematics": "math",
    "data structures": "data structures",
    "dsu": "dsu",
    "two pointers": "two pointers",
    "bit manipulation": "bitmasks",
    "bitmasks": "bitmasks",
    "arrays": "data structures",
    "sorting": "sortings",
}

class CodeforcesClient:
    _cache: Dict[str, Any] = {}
    _cache_time: float = 0.0
    _CACHE_TTL_SECONDS: float = 600.0  # 10 minutes cache

    @classmethod
    def _generate_api_signature(cls, method_name: str, params: Dict[str, str]) -> Dict[str, str]:
        api_key = settings.CF_API_KEY
        api_secret = settings.CF_API_SECRET
        if not api_key or not api_secret:
            return params

        updated_params = dict(params)
        updated_params["apiKey"] = api_key
        updated_params["time"] = str(int(time.time()))

        rand_prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        sorted_pairs = sorted(updated_params.items())
        query_string = "&".join(f"{k}={v}" for k, v in sorted_pairs)
        sig_base = f"{rand_prefix}/{method_name}?{query_string}#{api_secret}"
        hash_digest = hashlib.sha512(sig_base.encode("utf-8")).hexdigest()
        updated_params["apiSig"] = f"{rand_prefix}{hash_digest}"
        return updated_params

    @classmethod
    async def fetch_problems(
        cls,
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        now = time.time()
        cf_tags_arg = ""
        if tags:
            normalized_tags = [TAG_MAPPING.get(t.lower().strip(), t.lower().strip()) for t in tags]
            cf_tags_arg = ";".join(normalized_tags)

        cache_key = f"{cf_tags_arg}_{rating_min}_{rating_max}_{limit}"
        if cache_key in cls._cache and (now - cls._cache_time) < cls._CACHE_TTL_SECONDS:
            return cls._cache[cache_key]

        params: Dict[str, str] = {}
        if cf_tags_arg:
            params["tags"] = cf_tags_arg

        signed_params = cls._generate_api_signature("problemset.problems", params)
        url = "https://codeforces.com/api/problemset.problems"

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(url, params=signed_params)
                if resp.status_code != 200:
                    logger.warning(f"Codeforces API error: {resp.status_code} - {resp.text[:200]}")
                    return []

                payload = resp.json()
                if payload.get("status") != "OK":
                    logger.warning(f"Codeforces returned non-OK status: {payload.get('comment')}")
                    return []

                result = payload.get("result", {})
                raw_problems = result.get("problems", [])
                filtered: List[Dict[str, Any]] = []

                for p in raw_problems:
                    r = p.get("rating")
                    if rating_min is not None and (r is None or r < rating_min):
                        continue
                    if rating_max is not None and (r is None or r > rating_max):
                        continue
                    filtered.append(cls._format_problem(p))
                    if len(filtered) >= limit:
                        break

                cls._cache[cache_key] = filtered
                cls._cache_time = now
                return filtered
        except Exception as e:
            logger.error(f"Failed to fetch problems from Codeforces API: {e}")
            return []

    _problem_registry: Dict[str, Any] = {}

    @classmethod
    def get_coding_problem_by_id(cls, slug_id: str) -> Optional[Any]:
        if slug_id in cls._problem_registry:
            return cls._problem_registry[slug_id]

        # Parse slug formatted like 'cf-1800-c'
        parts = slug_id.lower().split("-")
        if len(parts) >= 3 and parts[0] == "cf":
            try:
                contest_id = int(parts[1])
                index = parts[2].upper()
                prob_dict = cls._format_problem({
                    "contestId": contest_id,
                    "index": index,
                    "name": f"Competitive Challenge {index}",
                    "rating": 1200,
                    "tags": ["algorithms", "implementation"],
                })
                from backend.app.coding.problems import CodingProblem
                cp = CodingProblem(**prob_dict)
                cls._problem_registry[slug_id] = cp
                return cp
            except Exception as e:
                logger.warning(f"Could not build CodingProblem for slug {slug_id}: {e}")
        return None

    @classmethod
    def _format_problem(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        contest_id = raw.get("contestId")
        index = raw.get("index")
        name = raw.get("name", "Competitive Programming Challenge")
        rating = raw.get("rating", 1200)
        tags = raw.get("tags", [])
        slug_id = f"cf-{contest_id}-{index}".lower()

        if rating < 1300:
            difficulty = "easy"
        elif rating < 1800:
            difficulty = "medium"
        else:
            difficulty = "hard"

        cf_url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"

        starter_code_py = (
            f"import sys\n\n"
            f"# Codeforces #{contest_id}{index} — {name}\n"
            f"# Difficulty Rating: {rating} | Tags: {', '.join(tags)}\n"
            f"# Link: {cf_url}\n\n"
            f"def solve():\n"
            f"    # TODO: Implement your solution here\n"
            f"    lines = sys.stdin.read().split()\n"
            f"    if not lines:\n"
            f"        return\n"
            f"    # Parse input and output answer\n"
            f"    pass\n\n"
            f"if __name__ == '__main__':\n"
            f"    solve()\n"
        )

        starter_code_cpp = (
            f"#include <iostream>\n"
            f"#include <vector>\n"
            f"#include <string>\n"
            f"#include <algorithm>\n\n"
            f"// Codeforces #{contest_id}{index} — {name}\n"
            f"// Rating: {rating} | Tags: {', '.join(tags)}\n"
            f"// Link: {cf_url}\n\n"
            f"using namespace std;\n\n"
            f"void solve() {{\n"
            f"    // TODO: Implement your solution here\n"
            f"}}\n\n"
            f"int main() {{\n"
            f"    ios_base::sync_with_stdio(false);\n"
            f"    cin.tie(NULL);\n"
            f"    solve();\n"
            f"    return 0;\n"
            f"}}\n"
        )

        starter_code_java = (
            f"import java.io.*;\n"
            f"import java.util.*;\n\n"
            f"// Codeforces #{contest_id}{index} — {name}\n"
            f"// Rating: {rating} | Tags: {', '.join(tags)}\n"
            f"// Link: {cf_url}\n\n"
            f"public class Solution {{\n"
            f"    public static void main(String[] args) throws IOException {{\n"
            f"        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n"
            f"        // TODO: Implement your solution here\n"
            f"    }}\n"
            f"}}\n"
        )

        prob_dict = {
            "id": slug_id,
            "contest_id": contest_id,
            "index": index,
            "title": f"CF #{contest_id}{index}: {name}",
            "name": name,
            "rating": rating,
            "difficulty": difficulty,
            "category": tags[0] if tags else "algorithms",
            "tags": tags,
            "url": cf_url,
            "description": (
                f"### Codeforces #{contest_id}{index} — {name}\n\n"
                f"- **Rating**: `{rating}` ({difficulty.capitalize()})\n"
                f"- **Topics**: `{', '.join(tags)}`\n"
                f"- **Problem URL**: [{name} on Codeforces]({cf_url})\n\n"
                f"This challenge is fetched live from Codeforces for competitive algorithmic practice. "
                f"Inspect the problem description and constraints on Codeforces. Write your standard I/O solution below."
            ),
            "input_format": "Standard Input (stdin). Process input stream as specified on Codeforces.",
            "output_format": "Standard Output (stdout). Print solution to stdout.",
            "constraints": [
                f"Difficulty Rating: {rating}",
                "Time limit: 2.0s per test",
                "Memory limit: 256MB",
                f"Algorithmic Tags: {', '.join(tags)}",
            ],
            "starter_code": {
                "python": starter_code_py,
                "cpp": starter_code_cpp,
                "java": starter_code_java,
            },
            "sample_test_cases": [
                {"stdin": "", "expected_stdout": ""}
            ],
            "test_cases": [
                {"stdin": "", "expected_stdout": "", "is_hidden": False}
            ],
            "ai_coaching_supported": True,
            "source": "codeforces",
        }

        try:
            from backend.app.coding.problems import CodingProblem
            cls._problem_registry[slug_id] = CodingProblem(**prob_dict)
        except Exception:
            pass

        return prob_dict

    @classmethod
    async def get_recommended_for_interview(
        cls,
        difficulty: str = "intermediate",
        domain_skills: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        diff = difficulty.lower()
        if diff in ("easy", "beginner"):
            r_min, r_max = 800, 1200
        elif diff in ("hard", "advanced"):
            r_min, r_max = 1700, 2400
        else:
            r_min, r_max = 1200, 1700

        matched_tags: List[str] = []
        if domain_skills:
            for s in domain_skills:
                for k, v in TAG_MAPPING.items():
                    if k in s.lower():
                        matched_tags.append(v)
                        break

        problems = await cls.fetch_problems(
            rating_min=r_min,
            rating_max=r_max,
            tags=list(set(matched_tags)) if matched_tags else None,
            limit=limit,
        )
        return problems
