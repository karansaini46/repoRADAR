import httpx
from bs4 import BeautifulSoup
from typing import List
from loguru import logger

async def detect_tech_stack(website_url: str) -> List[str]:
    """
    Detect the technology stack used by a website by analyzing HTTP headers and HTML content.
    Returns a list of detected technologies.
    """
    if not website_url:
        return []

    # Ensure URL has scheme
    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"

    stack = set()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
            try:
                response = await client.get(website_url, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.debug(f"Failed to fetch {website_url} for tech stack detection: {e}")
                return []
            
            # Analyze headers
            resp_headers = {k.lower(): v.lower() for k, v in response.headers.items()}
            
            # Hosting / Cloud
            if "x-vercel-id" in resp_headers or "vercel" in resp_headers.get("server", ""):
                stack.add("Vercel")
            if "x-amz-cf-id" in resp_headers or "aws" in resp_headers.get("server", ""):
                stack.add("AWS")
            if "cloudflare" in resp_headers.get("server", ""):
                stack.add("Cloudflare")
            if "netlify" in resp_headers.get("server", ""):
                stack.add("Netlify")
                
            # Frameworks in headers
            powered_by = resp_headers.get("x-powered-by", "")
            if "express" in powered_by:
                stack.add("Express")
            if "next.js" in powered_by:
                stack.add("Next.js")
            if "php" in powered_by:
                stack.add("PHP")

            # Analyze HTML
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Frameworks from HTML
            if "id=\"__next\"" in html or "_next/static" in html:
                stack.add("Next.js")
            if "id=\"___gatsby\"" in html:
                stack.add("Gatsby")
            if "data-reactroot" in html or "react" in html.lower():
                stack.add("React")
            if "nuxt" in html.lower():
                stack.add("Nuxt.js")
            if "django" in html.lower() or "csrfmiddlewaretoken" in html:
                stack.add("Django")
            if "authenticity_token" in html: # Common in Rails
                stack.add("Ruby on Rails")
                
            # Payment processors
            if "js.stripe.com" in html or "stripe" in html.lower():
                stack.add("Stripe")
            if "paddle.com" in html:
                stack.add("Paddle")
                
            # Analytics
            if "google-analytics.com" in html or "gtag" in html:
                stack.add("Google Analytics")
            if "segment.com" in html:
                stack.add("Segment")
            if "mixpanel.com" in html:
                stack.add("Mixpanel")
            if "plausible.io" in html:
                stack.add("Plausible")
                
            # Auth
            if "auth0.com" in html:
                stack.add("Auth0")
            if "clerk.dev" in html or "clerk.com" in html:
                stack.add("Clerk")
            if "supabase" in html.lower():
                stack.add("Supabase")

    except Exception as e:
        logger.debug(f"Error during tech stack detection for {website_url}: {e}")

    return list(stack)
