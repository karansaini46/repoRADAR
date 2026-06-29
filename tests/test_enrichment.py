import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from autoscan.shared.db.models import Company
from autoscan.enrichment.scorer import CompanyScorer
from autoscan.enrichment.dns_check import check_domain
from autoscan.enrichment.pipeline import extract_domain

def test_extract_domain():
    assert extract_domain("https://www.example.com/path") == "example.com"
    assert extract_domain("http://startup.io") == "startup.io"
    assert extract_domain("github.io/user") == "github.io"
    assert extract_domain("") == ""

def test_scorer_high():
    scorer = CompanyScorer()
    company = Company(github_org="testorg", website="https://custom.com", employee_count=0)
    
    enrichment = {
        "employees": 100, # >50: +0.25
        "funding_stage": "Series A", # +0.20
        "has_mx": True, # +0.10
        "tech_stack": ["AWS", "Stripe", "React"], # +0.15
        "total_github_stars": 600, # +0.10
        "days_since_last_commit": 10, # +0.10
        "hiring": True # +0.10
    }
    
    score = scorer.score(company, enrichment)
    assert score == 1.0 # 0.25 + 0.20 + 0.10 + 0.15 + 0.10 + 0.10 + 0.10 = 1.0

def test_scorer_low():
    scorer = CompanyScorer()
    company = Company(github_org="testorg", website="https://testorg.github.io", employee_count=2)
    
    enrichment = {
        "employees": 5,
        "funding_stage": None,
        "has_mx": False,
        "tech_stack": ["React"], 
        "total_github_stars": 10,
        "days_since_last_commit": 100,
        "hiring": False
    }
    
    score = scorer.score(company, enrichment)
    assert score == 0.0

@pytest.mark.asyncio
@patch('autoscan.enrichment.dns_check.dns.resolver.resolve')
@patch('autoscan.enrichment.dns_check.whois.whois')
async def test_dns_check(mock_whois, mock_resolve):
    # Mock whois
    mock_w = MagicMock()
    mock_w.registrar = "NameCheap"
    mock_w.creation_date = datetime.now(timezone.utc) - timedelta(days=100)
    mock_whois.return_value = mock_w
    
    # Mock DNS
    mock_resolve.return_value = ["dummy_record"]
    
    result = await check_domain("example.com")
    
    assert result["has_mx"] is True
    assert result["has_a"] is True
    assert result["registrar"] == "NameCheap"
    assert result["domain_age_days"] == 100
    
