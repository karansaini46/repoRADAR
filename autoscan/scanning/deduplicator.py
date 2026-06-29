import logging
from typing import List

from autoscan.scanning.base_scanner import Finding, Severity

logger = logging.getLogger(__name__)

# Assign a numeric weight to severities to help pick the "highest"
_SEVERITY_WEIGHT = {
    Severity.CRITICAL: 50,
    Severity.HIGH: 40,
    Severity.MEDIUM: 30,
    Severity.LOW: 20,
    Severity.INFO: 10,
}

# Assign a numeric weight to confidence to help pick the "highest"
_CONFIDENCE_WEIGHT = {
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Unknown": 0,
}

def _get_severity_weight(severity: Severity) -> int:
    return _SEVERITY_WEIGHT.get(severity, 0)

def _get_confidence_weight(confidence: str) -> int:
    if not confidence:
        return 0
    return _CONFIDENCE_WEIGHT.get(confidence.title(), 0)

def deduplicate(findings: List[Finding]) -> List[Finding]:
    """
    Deduplicates findings.
    Logic: if same file_path + line_no +/- 3 lines and same type -> merge.
    Keep the finding with highest confidence/severity.
    """
    if not findings:
        return []

    original_count = len(findings)
    deduplicated_findings = []
    
    # Sort findings to ensure consistent processing, though not strictly required for the logic
    # Grouping by type and file_path makes it easier
    grouped = {}
    for finding in findings:
        key = (finding.type, finding.file_path)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(finding)

    for (ftype, fpath), group in grouped.items():
        # Findings with no line number can only be deduplicated if they are exactly the same type/file
        # We might want to keep all of them or merge all of them. Let's merge them all into one if no line no.
        
        merged_in_group = []
        
        for current in group:
            merged = False
            for existing in merged_in_group:
                # If neither has line_no, they match on type/file_path, merge them.
                if current.line_no is None and existing.line_no is None:
                    # They are essentially the same finding type in the same file without line info
                    match = True
                elif current.line_no is not None and existing.line_no is not None:
                    # Check +/- 3 lines
                    match = abs(current.line_no - existing.line_no) <= 3
                else:
                    # One has line no, one doesn't. Treat as separate.
                    match = False
                    
                if match:
                    # Merge current into existing by keeping the one with higher severity/confidence
                    current_score = (_get_severity_weight(current.severity), _get_confidence_weight(current.confidence))
                    existing_score = (_get_severity_weight(existing.severity), _get_confidence_weight(existing.confidence))
                    
                    if current_score > existing_score:
                        # Replace existing with current
                        existing.severity = current.severity
                        existing.title = current.title
                        existing.description = current.description
                        existing.scanner_name = current.scanner_name
                        existing.confidence = current.confidence
                        existing.raw = current.raw
                        # We keep the line_no of the current since it 'won'
                        existing.line_no = current.line_no
                        
                    merged = True
                    break
            
            if not merged:
                merged_in_group.append(current)
                
        deduplicated_findings.extend(merged_in_group)

    merged_count = original_count - len(deduplicated_findings)
    logger.info(f"Deduplicated {merged_count} findings.")
    
    return deduplicated_findings
