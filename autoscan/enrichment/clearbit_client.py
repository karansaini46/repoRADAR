import httpx
from loguru import logger
from typing import Dict, Any

class ClearbitEnricher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Use httpx.AsyncClient with basic auth or Bearer token depending on Clearbit
        # Clearbit usually uses Basic Auth with the key as the username and empty password
        self.auth = (self.api_key, "")
        self.base_url = "https://company.clearbit.com/v2/companies/find"
        
    async def enrich_company(self, domain: str) -> Dict[str, Any]:
        """
        Enrich a company using Clearbit API.
        Gracefully falls back to an empty dict if the API is unavailable or returns an error.
        """
        if not self.api_key:
            logger.warning("No Clearbit API key provided, skipping enrichment.")
            return {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    self.base_url,
                    params={"domain": domain},
                    auth=self.auth
                )
                
                if response.status_code == 404:
                    logger.debug(f"Clearbit: No data found for {domain}")
                    return {}
                    
                response.raise_for_status()
                data = response.json()
                
                return {
                    "employees": data.get("metrics", {}).get("employees"),
                    "funding_stage": data.get("metrics", {}).get("fundingType"), # Clearbit might use different keys, e.g. raised or stage
                    "annual_revenue_range": data.get("metrics", {}).get("estimatedAnnualRevenue"),
                    "location": data.get("location"),
                    "industry": data.get("category", {}).get("industry")
                }
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"Clearbit API error for {domain}: HTTP {e.response.status_code}")
                return {}
            except httpx.RequestError as e:
                logger.warning(f"Clearbit request failed for {domain}: {e}")
                return {}
            except Exception as e:
                logger.warning(f"Unexpected error enriching {domain} with Clearbit: {e}")
                return {}
