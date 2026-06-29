import os
import logging
from typing import List
from pathlib import Path

from autoscan.shared.db.database import SessionLocal
from autoscan.shared.db.models import Finding as DBFinding, Repository
from autoscan.scanning.base_scanner import Finding, Severity
from autoscan.ai_layer.verifier import FindingVerifier

logger = logging.getLogger(__name__)

async def process_repo_findings(repo_id: int) -> List[dict]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set.")
        return []
        
    verifier = FindingVerifier(api_key=api_key, model='claude-3-5-sonnet-20240620')
    
    with SessionLocal() as db:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository with ID {repo_id} not found.")
            return []
            
        repo_path = Path(repo.local_path) if repo.local_path else None
        if not repo_path or not repo_path.exists():
            logger.error(f"Repository path for {repo.name} does not exist.")
            return []
            
        unverified_db_findings = db.query(DBFinding).filter(
            DBFinding.repository_id == repo_id,
            DBFinding.verified == False
        ).all()
        
        if not unverified_db_findings:
            logger.info(f"No unverified findings for repo {repo.name}.")
            return []
            
        logger.info(f"Processing {len(unverified_db_findings)} unverified findings for {repo.name}...")
        
        # Convert DBFindings to the dataclass Findings expected by verifier
        findings_to_verify = []
        for dbf in unverified_db_findings:
            # Note: DB stores severity as string, but BaseScanner.Finding expects Severity Enum
            # We map it back to enum for the verifier signature.
            severity_val = getattr(Severity, dbf.severity.upper(), Severity.INFO) if dbf.severity else Severity.INFO
            
            finding = Finding(
                type=dbf.type,
                severity=severity_val,
                title=dbf.title,
                description=dbf.description,
                file_path=dbf.file_path,
                line_no=dbf.line_no,
                scanner_name=dbf.scanner_name,
                confidence=dbf.confidence,
                raw=dbf.raw_data
            )
            findings_to_verify.append(finding)
            
        # Verify in batches (handled internally by verifier.verify_batch)
        verification_results = await verifier.verify_batch(findings_to_verify, repo_path)
        
        # Update DB
        for dbf, v_res in zip(unverified_db_findings, verification_results):
            if not v_res:
                continue
                
            dbf.verified = True
            dbf.is_false_positive = v_res.get('is_false_positive', False)
            
            # Combine business and technical explanation
            ai_explanation = ""
            if v_res.get('business_risk_explanation'):
                ai_explanation += f"**Business Risk:**\n{v_res.get('business_risk_explanation')}\n\n"
            if v_res.get('technical_explanation'):
                ai_explanation += f"**Technical Details:**\n{v_res.get('technical_explanation')}"
            
            dbf.ai_explanation = ai_explanation.strip()
            dbf.ai_recommendation = v_res.get('recommended_fix', '')
            dbf.verified_severity = v_res.get('verified_severity', dbf.severity)
            dbf.fix_hours_estimate = v_res.get('estimated_fix_hours', 0)
            
            # Optionally update title if a better one was provided and it's a real issue
            if not dbf.is_false_positive and v_res.get('plain_english_title'):
                dbf.title = v_res.get('plain_english_title')
                
        db.commit()
        
        # Rough token/cost estimation (very rough based on standard prompt size and response)
        # Assuming ~1000 input tokens per prompt, ~300 output tokens.
        estimated_input_tokens = len(unverified_db_findings) * 1000
        estimated_output_tokens = len(unverified_db_findings) * 300
        # claude-3-5-sonnet: $3 / M input, $15 / M output
        estimated_cost = (estimated_input_tokens / 1000000 * 3) + (estimated_output_tokens / 1000000 * 15)
        
        logger.info(f"Verified {len(unverified_db_findings)} findings for {repo.name}.")
        logger.info(f"Estimated Token Usage: {estimated_input_tokens} input, {estimated_output_tokens} output")
        logger.info(f"Estimated Cost: ${estimated_cost:.4f}")
        
        return verification_results
