from typing import Dict, Any
from autoscan.shared.db.models import Company
from loguru import logger

class CompanyScorer:
    def __init__(self):
        self.enterprise_tools = {"Stripe", "Auth0", "AWS", "Google Analytics", "Mixpanel", "Segment"}

    def score(self, company: Company, enrichment: Dict[str, Any]) -> float:
        """
        Score an enriched company to determine business impact.
        Returns a float between 0.0 and 1.0.
        """
        score = 0.0
        reasons = []

        # 1. Employee Count
        employee_count = enrichment.get("employees") or company.employee_count or 0
        if employee_count > 50:
            score += 0.25
            reasons.append("employee_count>50")
        elif employee_count > 10:
            score += 0.15
            reasons.append("employee_count>10")

        # 2. Funding
        funding = enrichment.get("funding_stage")
        if funding:
            score += 0.20
            reasons.append("has_funding")

        # 3. Custom Domain
        # If the domain is not a common provider like github.io, vercel.app, etc.
        # DNS check tells us if it has MX or A records, which typically means it's custom.
        has_mx = enrichment.get("has_mx", False)
        if has_mx or (company.website and "github.io" not in company.website):
            score += 0.10
            reasons.append("has_custom_domain")

        # 4. Enterprise Tech Stack
        tech_stack = enrichment.get("tech_stack", [])
        if any(tool in self.enterprise_tools for tool in tech_stack):
            score += 0.15
            reasons.append("has_enterprise_tools")

        # 5. GitHub Stars > 500 (across repos)
        # For simplicity, if enrichment provides total_stars or we calculate it
        total_stars = enrichment.get("total_github_stars", 0)
        if total_stars > 500:
            score += 0.10
            reasons.append("github_stars>500")

        # 6. Recent Activity
        recent_activity = enrichment.get("days_since_last_commit")
        if recent_activity is not None and recent_activity < 30:
            score += 0.10
            reasons.append("recent_activity<30")

        # 7. Hiring
        hiring = enrichment.get("hiring", False)
        if hiring:
            score += 0.10
            reasons.append("hiring")

        final_score = min(score, 1.0)
        
        logger.info(
            f"Company {company.github_org} enriched score: {final_score:.2f}",
            score=final_score,
            reasons=reasons
        )
        
        return final_score
