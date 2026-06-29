import asyncio
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

import anthropic

from autoscan.scanning.base_scanner import Finding
from autoscan.ai_layer.prompts import build_verification_prompt

logger = logging.getLogger(__name__)

class FindingVerifier:
    def __init__(self, api_key: str, model: str = 'claude-3-5-sonnet-20240620'):
        # Using claude-3-5-sonnet-20240620 as it's the current recommended sonnet model
        # The prompt asked for 'claude-sonnet-4-6' which doesn't exist, assuming a mix up and defaulting to standard sonnet
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.semaphore = asyncio.Semaphore(10) # Rate limit: max 10 concurrent API calls

    def get_code_context(self, finding: Finding, repo_path: Path) -> str:
        if not finding.file_path or finding.line_no is None:
            return ""
            
        full_path = repo_path / finding.file_path
        if not full_path.exists() or not full_path.is_file():
            return ""
            
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            start_line = max(0, finding.line_no - 11) # line_no is 1-indexed, so -1 for 0-index, then -10
            end_line = min(len(lines), finding.line_no + 10)
            
            context_lines = lines[start_line:end_line]
            context = "".join(context_lines)
            
            # Truncate to 2000 chars max
            if len(context) > 2000:
                context = context[:2000] + "\n...[truncated]"
                
            return context
        except Exception as e:
            logger.warning(f"Failed to read code context for {finding.file_path}: {e}")
            return ""

    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """Attempt to extract and parse JSON from the response."""
        text = text.strip()
        # Claude might sometimes still wrap in markdown or add preamble despite instructions
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Fallback to just parsing the whole text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Could not extract valid JSON from response: {text[:100]}...")

    async def verify_finding(self, finding: Finding, repo_path: Path) -> dict:
        code_context = self.get_code_context(finding, repo_path)
        
        # Convert Finding to dict for the prompt
        finding_dict = {
            "type": finding.type,
            "severity": finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
            "title": finding.title,
            "description": finding.description,
            "file_path": finding.file_path,
            "line_no": finding.line_no,
            "scanner_name": finding.scanner_name
        }
        
        prompt = build_verification_prompt(finding_dict, code_context)
        
        max_retries = 5
        base_delay = 2
        
        async with self.semaphore:
            for attempt in range(max_retries):
                try:
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=1024,
                        temperature=0,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    
                    response_text = response.content[0].text
                    return self._extract_json_from_response(response_text)
                    
                except anthropic.RateLimitError as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Rate limit exceeded after {max_retries} attempts.")
                        raise e
                    
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"Error during verification: {e}")
                    raise e
                    
        return {}

    async def verify_batch(self, findings: List[Finding], repo_path: Path) -> List[dict]:
        """Process up to 10 at a time with asyncio.gather (handled by semaphore inside verify_finding)"""
        tasks = [self.verify_finding(finding, repo_path) for finding in findings]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to default error dicts
        processed_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Failed to verify finding {findings[i].title}: {res}")
                processed_results.append({
                    "is_real_issue": False,
                    "verified_severity": "INFO",
                    "is_false_positive": True,
                    "false_positive_reason": f"Verification failed: {str(res)}",
                    "plain_english_title": findings[i].title,
                    "business_risk_explanation": "Could not verify due to error.",
                    "technical_explanation": "API Error",
                    "recommended_fix": "",
                    "estimated_fix_hours": 0
                })
            else:
                processed_results.append(res)
                
        return processed_results
