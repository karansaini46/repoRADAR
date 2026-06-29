import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from autoscan.ai_layer.verifier import FindingVerifier
from autoscan.scanning.base_scanner import Finding, Severity

@pytest.fixture
def dummy_finding():
    return Finding(
        type="SAST",
        severity=Severity.HIGH,
        title="SQL Injection",
        description="Potential SQL injection",
        file_path="src/db.py",
        line_no=15,
        scanner_name="semgrep"
    )

@pytest.mark.asyncio
async def test_extract_json_from_response(dummy_finding):
    verifier = FindingVerifier(api_key="dummy")
    
    # Test valid JSON with markdown wrapper
    markdown_resp = '''Here is the result:
```json
{
  "is_real_issue": true,
  "verified_severity": "HIGH",
  "is_false_positive": false,
  "false_positive_reason": null,
  "plain_english_title": "SQL Injection in User Query",
  "business_risk_explanation": "Risk 1",
  "technical_explanation": "Tech 1",
  "recommended_fix": "Fix 1",
  "estimated_fix_hours": 2
}
```'''
    result = verifier._extract_json_from_response(markdown_resp)
    assert result["is_real_issue"] is True
    assert result["estimated_fix_hours"] == 2

    # Test raw JSON
    raw_json = '{"is_real_issue": false, "estimated_fix_hours": 0}'
    result = verifier._extract_json_from_response(raw_json)
    assert result["is_real_issue"] is False

    # Test malformed JSON raises ValueError
    with pytest.raises(ValueError):
        verifier._extract_json_from_response("This is just some text without valid JSON.")

@pytest.mark.asyncio
@patch("autoscan.ai_layer.verifier.anthropic.AsyncAnthropic")
async def test_verify_finding(mock_anthropic_class, dummy_finding):
    # Setup mock
    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"is_real_issue": true, "estimated_fix_hours": 5}')]
    mock_client.messages.create.return_value = mock_message
    mock_anthropic_class.return_value = mock_client

    verifier = FindingVerifier(api_key="dummy")
    
    with patch.object(verifier, 'get_code_context', return_value="def query(user_id): return f'SELECT * FROM users WHERE id = {user_id}'"):
        result = await verifier.verify_finding(dummy_finding, Path("/dummy"))
        assert result["is_real_issue"] is True
        assert result["estimated_fix_hours"] == 5

@pytest.mark.asyncio
@patch("autoscan.ai_layer.verifier.anthropic.AsyncAnthropic")
async def test_verify_batch_rate_limiting(mock_anthropic_class, dummy_finding):
    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"is_real_issue": true, "estimated_fix_hours": 1}')]
    # Add a slight delay to simulate API call
    async def mock_create(*args, **kwargs):
        await asyncio.sleep(0.01)
        return mock_message
        
    mock_client.messages.create = mock_create
    mock_anthropic_class.return_value = mock_client

    verifier = FindingVerifier(api_key="dummy")
    
    findings = [dummy_finding] * 15 # 15 findings, semaphore limit is 10
    
    with patch.object(verifier, 'get_code_context', return_value="some context"):
        results = await verifier.verify_batch(findings, Path("/dummy"))
        
    assert len(results) == 15
    for r in results:
        assert r["is_real_issue"] is True
