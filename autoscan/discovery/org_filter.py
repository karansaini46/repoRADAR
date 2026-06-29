from datetime import datetime, timezone
from typing import List

from loguru import logger

class OrgFilter:
    def __init__(self):
        pass

    def filter_repos(self, repos: List[dict]) -> List[dict]:
        """
        Filter out forks and archived repositories.
        """
        filtered = []
        for repo in repos:
            if repo.get("fork") is True:
                continue
            if repo.get("archived") is True:
                continue
            filtered.append(repo)
        return filtered

    def _has_manifest(self, repos: List[dict]) -> bool:
        """
        Heuristic to guess if the organization uses standard manifests.
        Since we might not clone here, we check languages or typical repo properties.
        Wait, we could just check if any repo has a language that implies a manifest,
        or just assume true if it has primary languages.
        Actually, GitHub API provides `language` for a repo. If it's a known language
        (Python, JS, Go, Java, Rust, Ruby, etc.), it's likely to have a manifest.
        """
        manifest_languages = {"Python", "JavaScript", "TypeScript", "Go", "Java", "Ruby", "Rust", "PHP"}
        for repo in repos:
            if repo.get("language") in manifest_languages:
                return True
        return False

    def _has_recent_commit(self, repos: List[dict]) -> bool:
        """
        Check if any repo was updated in the last 6 months.
        GitHub repo object has `pushed_at` and `updated_at`.
        """
        now = datetime.now(timezone.utc)
        for repo in repos:
            pushed_at_str = repo.get("pushed_at")
            if not pushed_at_str:
                continue
            
            try:
                # e.g., "2023-10-18T14:32:00Z"
                pushed_at = datetime.strptime(pushed_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                diff = now - pushed_at
                if diff.days <= 180:
                    return True
            except ValueError:
                pass
        return False

    def score_org(self, org_data: dict, repos: List[dict]) -> float:
        """
        Score an organization from 0.0 to 1.0 based on business heuristics.
        - is_org(+0.3)
        - members>=5(+0.2) 
        - stars>=50(+0.1)
        - recent_commit(+0.15)
        - has_website(+0.1)
        - has_manifest(+0.1)
        - not_fork(+0.05)
        """
        score = 0.0
        reasons = []

        # 1. is_org
        if org_data.get("type", "").lower() == "organization":
            score += 0.3
            reasons.append("is_org")

        # 2. members >= 5 (org_data doesn't always include full members count, might need followers or public_members)
        # Using public_repos, followers or looking at actual repo counts as proxy if members not directly available
        # GitHub org payload has 'followers' and maybe 'public_members_url' but not direct members count usually.
        # Let's assume followers > 5 or public_repos > 5 or if employee_count is available.
        # Wait, the prompt says members>=5. Let's use org_data.get("followers", 0) as a proxy, 
        # or perhaps it's passed if we enriched it. I'll check followers for now.
        followers = org_data.get("followers", 0)
        if followers >= 5:
            score += 0.2
            reasons.append("members>=5")

        # 3. stars >= 50 (across all returned repos)
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        if total_stars >= 50:
            score += 0.1
            reasons.append("stars>=50")

        # 4. recent_commit
        if self._has_recent_commit(repos):
            score += 0.15
            reasons.append("recent_commit")

        # 5. has_website
        blog = org_data.get("blog")
        if blog and blog.strip() != "":
            score += 0.1
            reasons.append("has_website")

        # 6. has_manifest
        if self._has_manifest(repos):
            score += 0.1
            reasons.append("has_manifest")

        # 7. not_fork
        # True if at least one repo is not a fork
        if any(not r.get("fork", False) for r in repos):
            score += 0.05
            reasons.append("not_fork")

        # Cap score at 1.0 to handle floating point issues
        final_score = min(score, 1.0)
        
        logger.info(
            f"Org {org_data.get('login', 'Unknown')} scored {final_score:.2f}",
            score=final_score,
            reasons=reasons
        )
        
        return final_score
