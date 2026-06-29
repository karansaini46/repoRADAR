import logging
import httpx
from typing import List, Dict

logger = logging.getLogger(__name__)

class HunterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hunter.io/v2"

    async def find_emails(self, domain: str, role: str = 'engineering') -> List[Dict]:
        """
        Uses Hunter.io domain search API to find emails matching a specific role (department).
        In Hunter, role usually maps to 'department' like 'engineering', 'it', 'executive'.
        """
        if not self.api_key:
            return []

        # Hunter uses department, not role, but we'll adapt
        params = {
            "domain": domain,
            "department": role,
            "api_key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/domain-search", params=params)
                if resp.status_code != 200:
                    logger.warning(f"Hunter domain search failed for {domain}: {resp.status_code}")
                    return []
                    
                data = resp.json()
                emails = data.get('data', {}).get('emails', [])
                
                results = []
                for email_obj in emails:
                    results.append({
                        "email": email_obj.get('value'),
                        "first_name": email_obj.get('first_name'),
                        "last_name": email_obj.get('last_name'),
                        "position": email_obj.get('position'),
                        "confidence": email_obj.get('confidence')
                    })
                return results
        except Exception as e:
            logger.error(f"Error querying Hunter for {domain}: {e}")
            return []

    async def verify_email(self, email: str) -> Dict:
        """
        Uses Hunter.io email verifier API to check if an email is valid.
        """
        if not self.api_key:
            return {"valid": False, "score": 0}

        params = {
            "email": email,
            "api_key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/email-verifier", params=params)
                if resp.status_code != 200:
                    logger.warning(f"Hunter email verify failed for {email}: {resp.status_code}")
                    return {"valid": False, "score": 0}
                    
                data = resp.json()
                result_data = data.get('data', {})
                
                # status can be valid, invalid, accept_all, webmail, disposable, unknown
                is_valid = result_data.get('status') == 'valid'
                score = result_data.get('score', 0)
                
                return {"valid": is_valid, "score": score}
        except Exception as e:
            logger.error(f"Error verifying email {email} with Hunter: {e}")
            return {"valid": False, "score": 0}
