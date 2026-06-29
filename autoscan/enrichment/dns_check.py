import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

import dns.resolver
import whois
from loguru import logger

def _sync_check_domain(domain: str) -> Dict[str, Any]:
    """Synchronous implementation of DNS checking."""
    result = {
        "has_mx": False,
        "has_a": False,
        "domain_age_days": None,
        "registrar": None,
    }
    
    # 1. DNS lookups using dnspython
    try:
        mx_records = dns.resolver.resolve(domain, 'MX', lifetime=5.0)
        result["has_mx"] = len(mx_records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout, Exception):
        result["has_mx"] = False

    try:
        a_records = dns.resolver.resolve(domain, 'A', lifetime=5.0)
        result["has_a"] = len(a_records) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout, Exception):
        result["has_a"] = False
        
    # 2. WHOIS lookup for domain age and registrar
    try:
        w = whois.whois(domain)
        
        if w.registrar:
            if isinstance(w.registrar, list):
                result["registrar"] = w.registrar[0]
            else:
                result["registrar"] = w.registrar
                
        creation_date = w.creation_date
        if creation_date:
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            
            if isinstance(creation_date, datetime):
                # Ensure timezone aware for math
                if creation_date.tzinfo is None:
                    creation_date = creation_date.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                diff = now - creation_date
                result["domain_age_days"] = diff.days

    except Exception as e:
        logger.debug(f"WHOIS lookup failed for {domain}: {e}")

    return result

async def check_domain(domain: str) -> Dict[str, Any]:
    """
    Check DNS records and domain age asynchronously.
    Returns: {has_mx, has_a, domain_age_days, registrar}
    """
    # Use asyncio.to_thread to avoid blocking the event loop with synchronous network calls
    try:
        return await asyncio.to_thread(_sync_check_domain, domain)
    except Exception as e:
        logger.warning(f"Error checking domain {domain}: {e}")
        return {
            "has_mx": False,
            "has_a": False,
            "domain_age_days": None,
            "registrar": None,
        }
