"""csv_loader.py — Real LeetCode Questions Loader from liquidslr/leetcode-company-wise-problems

Reads 5. All.csv from data/leetcode_company_wise/<Company>/5. All.csv,
mapping exact LeetCode problem URLs, titles, frequencies, acceptance rates, and topics.
"""

import os
import csv
from typing import Any, Dict, List, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

REPO_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "leetcode_company_wise")

# Normalized directory mapping for companies with aliases or special folder names
COMPANY_FOLDER_ALIASES: Dict[str, str] = {
    "palantir": "Palantir Technologies",
    "palantir technologies": "Palantir Technologies",
    "walmart": "Walmart Labs",
    "walmart labs": "Walmart Labs",
    "square": "Block",
    "block": "Block",
    "tcs": "tcs",
    "tcs digital": "tcs",
    "tcs-digital": "tcs",
    "twitter": "X",
    "x": "X",
    "de-shaw": "D. E. Shaw",
    "d-e-shaw": "D. E. Shaw",
    "d. e. shaw": "D. E. Shaw",
    "jp-morgan": "JPMorgan Chase",
    "jpmorgan": "JPMorgan Chase",
    "jpmorgan chase": "JPMorgan Chase",
    "morgan-stanley": "Morgan Stanley",
    "morgan stanley": "Morgan Stanley",
    "bank-of-america": "Bank of America",
    "bank of america": "Bank of America",
    "scale-ai": "Scale AI",
    "scale ai": "Scale AI",
    "goldman-sachs": "Goldman Sachs",
    "goldman sachs": "Goldman Sachs",
    "cisco": "Cisco",
    "intel": "Intel",
    "amd": "AMD",
    "qualcomm": "Qualcomm",
    "stripe": "Stripe",
    "airbnb": "Airbnb",
    "netflix": "Netflix",
    "meta": "Meta",
    "apple": "Apple",
    "amazon": "Amazon",
    "microsoft": "Microsoft",
    "google": "Google",
    "uber": "Uber",
    "openai": "OpenAI",
    "anthropic": "OpenAI",  # Fallback to top frontier AI problems
    "salesforce": "Salesforce",
    "adobe": "Adobe",
    "oracle": "Oracle",
    "bloomberg": "Bloomberg",
    "linkedin": "LinkedIn",
    "nvidia": "Nvidia",
    "tiktok": "TikTok",
    "spotify": "Spotify",
    "bytedance": "ByteDance",
    "atlassian": "Atlassian",
    "paypal": "PayPal",
    "snap": "Snap",
    "tesla": "Tesla",
    "databricks": "Databricks",
    "snowflake": "Snowflake",
    "pinterest": "Pinterest",
    "dropbox": "Dropbox",
    "zoho": "Zoho",
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "flipkart": "Flipkart",
    "paytm": "Paytm",
    "cred": "CRED",
    "ola": "Ola",
    "zepto": "Zepto",
    "razorpay": "Razorpay",
    "infosys": "Infosys",
    "wipro": "Wipro",
    "accenture": "Accenture",
    "cognizant": "Cognizant",
    "capgemini": "Capgemini",
}

def resolve_company_folder(company_name_or_slug: str) -> Optional[str]:
    """Resolve directory name inside data/leetcode_company_wise."""
    if not os.path.exists(REPO_BASE_DIR):
        logger.warning(f"LeetCode company repo not found at {REPO_BASE_DIR}")
        return None

    cleaned = company_name_or_slug.strip().lower()
    if cleaned in COMPANY_FOLDER_ALIASES:
        target = COMPANY_FOLDER_ALIASES[cleaned]
        if os.path.isdir(os.path.join(REPO_BASE_DIR, target)):
            return target

    # Try exact or case-insensitive match in directory listing
    for dirname in os.listdir(REPO_BASE_DIR):
        if dirname.lower() == cleaned:
            return dirname
        # Replace hyphens with spaces and test
        if dirname.lower() == cleaned.replace("-", " "):
            return dirname

    return None

@lru_cache(maxsize=128)
def load_company_problems_from_csv(company_name_or_slug: str) -> List[Dict[str, Any]]:
    """
    Loads all real LeetCode problems for a company from 5. All.csv.
    Returns list of dicts with:
      - title: str
      - slug: str (derived from real LeetCode Link)
      - leetcode_url: str (exact real URL)
      - difficulty: str ('EASY', 'MEDIUM', 'HARD')
      - frequency_score: float
      - acceptance_rate: float
      - topics: List[str]
      - order_index: int (1-based)
      - is_unlocked: bool (True for first 3 problems on Day 1)
    """
    folder = resolve_company_folder(company_name_or_slug)
    if not folder:
        logger.info(f"No CSV directory found for company: {company_name_or_slug}")
        return []

    csv_path = os.path.join(REPO_BASE_DIR, folder, "5. All.csv")
    if not os.path.exists(csv_path):
        logger.warning(f"5. All.csv missing in {csv_path}")
        return []

    problems: List[Dict[str, Any]] = []
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            order = 1
            for row in reader:
                link = (row.get("Link") or "").strip()
                if not link or "leetcode.com/problems/" not in link:
                    continue

                slug = link.rstrip("/").split("/")[-1].strip().lower()
                canonical_link = f"https://leetcode.com/problems/{slug}/"
                title = (row.get("Title") or slug.replace("-", " ").title()).strip()
                diff_raw = (row.get("Difficulty") or "MEDIUM").strip().upper()
                difficulty = diff_raw if diff_raw in {"EASY", "MEDIUM", "HARD"} else "MEDIUM"

                try:
                    freq = float(row.get("Frequency", 100.0) or 100.0)
                except ValueError:
                    freq = 100.0

                try:
                    acc = float(row.get("Acceptance Rate", 0.5) or 0.5)
                    # Some files have acceptance rate as percentage (e.g. 52.3) or ratio (0.523)
                    if acc > 1.0:
                        acc = acc / 100.0
                except ValueError:
                    acc = 0.5

                raw_topics = row.get("Topics") or ""
                topics = [t.strip() for t in raw_topics.split(",") if t.strip()]

                # First 3 problems are unlocked from Day 1
                is_unlocked = (order <= 3)

                problems.append({
                    "title": title,
                    "slug": slug,
                    "leetcode_url": canonical_link,
                    "difficulty": difficulty,
                    "frequency_score": freq,
                    "acceptance_rate": acc,
                    "topics": topics,
                    "order_index": order,
                    "is_unlocked": is_unlocked,
                })
                order += 1

    except Exception as e:
        logger.error(f"Error reading CSV for {company_name_or_slug}: {e}")

    return problems
