import json

def build_verification_prompt(finding: dict, code_context: str) -> str:
    """
    Build the verification prompt for Claude.
    The prompt instructs Claude to analyze a security finding against the provided code context
    and return ONLY a JSON response without any markdown wrappers or preamble.
    """
    
    prompt = f"""You are a senior Application Security Engineer. Your task is to verify a security finding reported by an automated scanner.
You must return your analysis as a raw JSON object. Do NOT wrap it in ```json ... ``` markdown blocks. Do NOT include any preamble or explanation outside the JSON.
Your response must be valid parseable JSON exactly matching the structure requested.

Finding Details:
{json.dumps(finding, indent=2)}

Code Context (surrounding lines):
{code_context if code_context else "No code context available."}

Analyze the finding and the code context to determine if this is a real security issue or a false positive.
Provide a clear, non-technical business risk explanation (2-3 sentences max).
Provide a detailed technical explanation of the issue (or why it is a false positive).
Provide a recommended fix. If it's a false positive, suggest how to ignore or suppress it.
Estimate the hours required to fix this issue (use integers, 0 if false positive).

Return ONLY a JSON object with exactly these keys:
{{
  "is_real_issue": bool,
  "verified_severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO",
  "is_false_positive": bool,
  "false_positive_reason": "string or null",
  "plain_english_title": "string",
  "business_risk_explanation": "string",
  "technical_explanation": "string",
  "recommended_fix": "string",
  "estimated_fix_hours": int
}}
"""
    return prompt
