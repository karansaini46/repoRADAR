import asyncio
import logging
import httpx
from typing import List, Dict

from autoscan.shared.db.models import Repository

logger = logging.getLogger(__name__)

class GitHubContactExtractor:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def get_contributor_emails(self, repo: Repository) -> List[Dict]:
        """
        Extract emails from git log of the cloned repository and enrich via GitHub API.
        Runs: git log --format='%an|%ae' | sort | uniq -c | sort -rn | head -20
        """
        if not repo.local_path:
            logger.warning(f"Repo {repo.full_name} has no local path. Skipping contributor extraction.")
            return []

        cmd = "git log --format='%an|%ae' | sort | uniq -c | sort -rn | head -20"
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo.local_path
            )
            
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error(f"Error running git log in {repo.local_path}: {stderr.decode()}")
                return []
                
            raw_output = stdout.decode().strip()
            if not raw_output:
                return []
                
            contacts = []
            lines = raw_output.split('\n')
            
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    parts = line.split(maxsplit=1)
                    if len(parts) != 2:
                        continue
                        
                    # Extract the name and email
                    name_email = parts[1].split('|')
                    if len(name_email) != 2:
                        continue
                        
                    name = name_email[0].strip()
                    email = name_email[1].strip().lower()
                    
                    # Filter out generic/bot emails
                    if "noreply@github.com" in email or "action@github.com" in email or "[bot]" in email:
                        continue
                        
                    # Find GitHub username by email using search API (simplified approach)
                    # Note: GitHub Search API is heavily rate-limited, but we'll try carefully
                    username = None
                    try:
                        resp = await client.get(f"https://api.github.com/search/users?q={email}")
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get('total_count', 0) > 0:
                                username = data['items'][0]['login']
                    except Exception as e:
                        logger.warning(f"Failed to find username for {email}: {e}")
                        
                    bio = None
                    followers = 0
                    if username:
                        try:
                            user_resp = await client.get(f"https://api.github.com/users/{username}")
                            if user_resp.status_code == 200:
                                user_data = user_resp.json()
                                bio = user_data.get('bio')
                                followers = user_data.get('followers', 0)
                                if not name and user_data.get('name'):
                                    name = user_data['name']
                        except Exception as e:
                            logger.warning(f"Failed to fetch profile for {username}: {e}")

                    contacts.append({
                        "username": username,
                        "name": name,
                        "email": email,
                        "bio": bio,
                        "followers": followers
                    })
                    
            return contacts
            
        except Exception as e:
            logger.error(f"Failed to extract contributor emails for {repo.full_name}: {e}")
            return []

    async def get_org_members(self, org_name: str) -> List[Dict]:
        """
        Fetch public members of the organization and enrich their profiles.
        """
        members = []
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                resp = await client.get(f"https://api.github.com/orgs/{org_name}/public_members")
                if resp.status_code != 200:
                    logger.warning(f"Could not fetch public members for {org_name}: {resp.status_code}")
                    return []
                    
                members_data = resp.json()
                
                # Limit to first 20 members to avoid rate limits during extraction
                for member in members_data[:20]:
                    username = member['login']
                    try:
                        user_resp = await client.get(f"https://api.github.com/users/{username}")
                        if user_resp.status_code == 200:
                            user_data = user_resp.json()
                            if user_data.get('email'): # Only care if they have a public email
                                members.append({
                                    "username": username,
                                    "name": user_data.get('name', username),
                                    "email": user_data.get('email'),
                                    "bio": user_data.get('bio'),
                                    "followers": user_data.get('followers', 0),
                                    "company": user_data.get('company')
                                })
                    except Exception as e:
                        logger.warning(f"Failed to fetch profile for {username}: {e}")
                        
            return members
        except Exception as e:
            logger.error(f"Error fetching org members for {org_name}: {e}")
            return []
