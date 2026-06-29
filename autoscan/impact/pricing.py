def determine_report_price(impact: dict, company: dict) -> dict:
    """
    Determines the pricing tier and price for the final report based on the estimated risk
    and the company's qualification/enrichment score.
    """
    
    total_risk = impact.get('total_max_usd', 0.0)
    critical_count = impact.get('critical_count', 0)
    company_score = company.get('qualification_score') or company.get('enrichment_score') or 0.0
    
    # Pricing tiers
    if total_risk > 500000.0 and company_score > 0.7:
        price_cents = 29900  # $299.00
        tier = 'enterprise'
        stripe_price_id_placeholder = "price_enterprise_placeholder"
    elif total_risk > 100000.0 or critical_count > 0:
        price_cents = 14900  # $149.00
        tier = 'professional'
        stripe_price_id_placeholder = "price_professional_placeholder"
    elif total_risk > 10000.0:
        price_cents = 7900  # $79.00
        tier = 'standard'
        stripe_price_id_placeholder = "price_standard_placeholder"
    else:
        price_cents = 4900  # $49.00
        tier = 'basic'
        stripe_price_id_placeholder = "price_basic_placeholder"
        
    return {
        "price_cents": price_cents,
        "tier": tier,
        "stripe_price_id_placeholder": stripe_price_id_placeholder
    }
