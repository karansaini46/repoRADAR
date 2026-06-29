from autoscan.reports.builder import ReportBuilder

company = {
    'id': 1,
    'name': 'Dummy Corp',
    'report_tier': 'enterprise',
    'estimated_risk_min_usd': 50000,
    'estimated_risk_max_usd': 1500000
}

impact = {
    'risk_summary': 'Extreme risk exposure.',
    'critical_count': 2,
    'high_count': 5,
    'medium_count': 10
}

findings = [
    {
        'verified_severity': 'CRITICAL',
        'title': 'Hardcoded AWS Key',
        'file_path': 'src/auth.py',
        'line_no': 42,
        'scanner_name': 'trufflehog',
        'ai_explanation': 'AWS Key found in code.',
        'ai_recommendation': 'Use AWS Secrets Manager.',
        'fix_hours_estimate': 4
    }
]

b = ReportBuilder()
b.build_full_report(company, impact, findings)
print("PDF Generated successfully.")
