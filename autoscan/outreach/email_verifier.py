import asyncio
import logging
import smtplib
import socket

# Try to import dns.resolver, fallback to aiodns if needed, but we'll try to just use asyncio's socket if possible
# Actually, standard asyncio doesn't do MX lookups easily. We'll use aiodns.
try:
    import aiodns
except ImportError:
    aiodns = None

logger = logging.getLogger(__name__)

async def get_mx_records(domain: str) -> list:
    if not aiodns:
        return []
    try:
        resolver = aiodns.DNSResolver()
        result = await resolver.query(domain, 'MX')
        # Sort by priority
        records = sorted(result, key=lambda r: r.priority)
        return [r.host for r in records]
    except Exception as e:
        logger.debug(f"MX lookup failed for {domain}: {e}")
        return []

async def verify_email_smtp(email: str) -> bool:
    """
    Do MX lookup for domain, attempt SMTP RCPT TO check.
    Return True if email likely exists.
    Timeout: 5 seconds, catch all exceptions gracefully.
    """
    if '@' not in email:
        return False
        
    domain = email.split('@')[1]
    
    try:
        # 1. MX Lookup
        # Timeout for entire operation
        async with asyncio.timeout(5.0):
            mx_hosts = await get_mx_records(domain)
            if not mx_hosts:
                # Fallback to A record if no MX
                mx_hosts = [domain]
                
            # 2. SMTP Check
            # We will use asyncio.to_thread to run standard smtplib to avoid dealing with raw async smtp protocol
            # which can be complex without aiosmtplib.
            def smtp_check(host):
                try:
                    server = smtplib.SMTP(host=host, timeout=3)
                    server.set_debuglevel(0)
                    
                    # Identify ourselves
                    server.helo(socket.getfqdn())
                    server.mail('hello@autoscan.security')
                    code, message = server.rcpt(str(email))
                    server.quit()
                    
                    # 250 is standard success. Some servers catch-all and return 250 anyway, but this is best-effort.
                    return code == 250
                except Exception as e:
                    logger.debug(f"SMTP check failed for {email} via {host}: {e}")
                    return False

            for mx in mx_hosts:
                result = await asyncio.to_thread(smtp_check, mx)
                if result:
                    return True
                    
            return False
            
    except TimeoutError:
        logger.warning(f"SMTP verification timed out for {email}")
        return False
    except Exception as e:
        logger.warning(f"SMTP verification error for {email}: {e}")
        return False
