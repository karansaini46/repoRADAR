import asyncio
import logging
from typing import List

from autoscan.shared.db.models import Company, Contact, Repository
from autoscan.outreach.github_contacts import GitHubContactExtractor
from autoscan.outreach.hunter_client import HunterClient
from autoscan.outreach.email_verifier import verify_email_smtp

logger = logging.getLogger(__name__)

class ContactDiscovery:
    def __init__(self, github_token: str, hunter_key: str = None):
        self.github_token = github_token
        self.hunter_key = hunter_key
        self.github_extractor = GitHubContactExtractor(token=github_token)
        self.hunter_client = HunterClient(api_key=hunter_key)

    def _score_contact(self, contact_info: dict) -> int:
        """
        Scores contacts based on relevance.
        security_title(+3), cto_vp(+2), engineering(+1), other(0)
        """
        score = 0
        
        # Combine bio, position, and name for role searching
        text_to_search = " ".join([
            str(contact_info.get('bio', '')),
            str(contact_info.get('position', '')),
        ]).lower()
        
        if 'security' in text_to_search or 'ciso' in text_to_search:
            score += 3
        elif 'cto' in text_to_search or 'chief technology' in text_to_search or 'vp' in text_to_search or 'vice president' in text_to_search or 'founder' in text_to_search:
            score += 2
        elif 'engineer' in text_to_search or 'developer' in text_to_search or 'lead' in text_to_search or 'engineering' in text_to_search:
            score += 1
            
        return score

    async def discover(self, company: Company, repositories: List[Repository]) -> List[Contact]:
        """
        Runs GitHub + Hunter extraction in parallel.
        Deduplicates by email.
        Scores contacts.
        Verifies top 3 emails.
        Returns ranked list of Contact objects (unsaved DB models).
        """
        tasks = []
        
        # 1. GitHub Extraction tasks
        for repo in repositories:
            tasks.append(self.github_extractor.get_contributor_emails(repo))
            
        if company.github_org:
            tasks.append(self.github_extractor.get_org_members(company.github_org))
            
        # 2. Hunter Extraction task
        domain = company.website
        if domain:
            # Clean domain URL
            domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
            if self.hunter_key:
                tasks.append(self.hunter_client.find_emails(domain))
            
        # Run all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_raw_contacts = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Error in contact extraction task: {res}")
            elif res:
                all_raw_contacts.extend(res)
                
        # Deduplicate and score
        unique_contacts_map = {}
        for rc in all_raw_contacts:
            email = rc.get('email')
            if not email:
                continue
                
            email = email.lower()
            if email not in unique_contacts_map:
                unique_contacts_map[email] = {
                    "email": email,
                    "first_name": rc.get('first_name') or (rc.get('name', '').split()[0] if rc.get('name') else None),
                    "last_name": rc.get('last_name') or (" ".join(rc.get('name', '').split()[1:]) if rc.get('name') else None),
                    "position": rc.get('position') or rc.get('bio'),
                    "score": 0,
                    "source": "github" if 'username' in rc else "hunter",
                    "is_verified": False
                }
            
            # Re-score and keep highest
            current_score = unique_contacts_map[email]['score']
            new_score = self._score_contact(rc)
            if new_score > current_score:
                unique_contacts_map[email]['score'] = new_score
                
        # Convert to list and sort by score
        contact_dicts = list(unique_contacts_map.values())
        contact_dicts.sort(key=lambda x: x['score'], reverse=True)
        
        # Verify top 3
        verify_tasks = []
        top_3 = contact_dicts[:3]
        for cd in top_3:
            verify_tasks.append(verify_email_smtp(cd['email']))
            
        verification_results = await asyncio.gather(*verify_tasks, return_exceptions=True)
        
        for i, v_res in enumerate(verification_results):
            if isinstance(v_res, Exception):
                logger.warning(f"Verification failed for {top_3[i]['email']}: {v_res}")
                top_3[i]['is_verified'] = False
            else:
                top_3[i]['is_verified'] = v_res
                
        # Build Contact models
        final_contacts = []
        for cd in contact_dicts:
            contact = Contact(
                company_id=company.id,
                email=cd['email'],
                first_name=cd['first_name'],
                last_name=cd['last_name'],
                position=cd['position'],
                score=cd['score'],
                source=cd['source'],
                is_verified=cd['is_verified']
            )
            final_contacts.append(contact)
            
        return final_contacts
