import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""
    pass

class GitHubRateLimitError(GitHubAPIError):
    """Exception raised when GitHub rate limit is exceeded."""
    pass

class GitHubSearcher:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(30.0),
            base_url="https://api.github.com",
        )

    async def close(self):
        await self.client.aclose()

    def _check_rate_limit(self, response: httpx.Response):
        """Check rate limit headers and log warnings if low."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            remaining = int(remaining)
            if remaining < 100:
                logger.warning(f"GitHub API rate limit low: {remaining} remaining. Resets at {reset_time}")

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, GitHubRateLimitError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _make_request(self, method: str, url: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        logger.debug(f"Making GitHub API request to {url} with params {params}")
        response = await self.client.request(method, url, params=params)
        
        self._check_rate_limit(response)

        if response.status_code in (403, 429):
            if "rate limit" in response.text.lower() or "secondary rate" in response.text.lower():
                logger.error(f"Rate limit exceeded: {response.text}")
                # Tenacity will retry this
                raise GitHubRateLimitError("Rate limit exceeded")
        
        response.raise_for_status()
        return response

    async def search_repos(
        self, query: str, min_stars: int, language: str, page: int = 1, per_page: int = 30
    ) -> Tuple[List[dict], bool]:
        """
        Search for repositories. Returns a tuple of (repositories, has_next_page).
        We use `page` as the cursor for the REST API.
        """
        q = f"{query} language:{language} stars:>={min_stars}"
        params = {
            "q": q,
            "sort": "stars",
            "order": "desc",
            "page": page,
            "per_page": per_page,
        }
        
        response = await self._make_request("GET", "/search/repositories", params=params)
        data = response.json()
        
        items = data.get("items", [])
        
        # Check if there's a next page
        has_next = "rel=\"next\"" in response.headers.get("link", "")
        
        return items, has_next

    async def get_org_metadata(self, org_name: str) -> dict:
        """
        Fetch organization or user metadata from GitHub.
        Falls back to user if it's not an organization.
        """
        try:
            # First try as org
            response = await self._make_request("GET", f"/orgs/{org_name}")
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                try:
                    # Fallback to user
                    response = await self._make_request("GET", f"/users/{org_name}")
                    return response.json()
                except httpx.HTTPStatusError as e2:
                    if e2.response.status_code == 404:
                        logger.warning(f"Could not find org or user: {org_name}")
                        return {}
                    raise e2
            raise e
