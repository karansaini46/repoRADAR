from typing import List

class ImpactCalculator:
    def calculate_finding_impact(self, finding: dict, company: dict) -> dict:
        """
        Calculates the financial impact of a single finding based on defined rules.
        """
        min_usd = 0.0
        max_usd = 0.0
        impact_type = "Unknown"
        one_liner = "No impact defined"

        finding_type = finding.get('type', '').lower()
        severity = finding.get('verified_severity', finding.get('severity', '')).upper()
        title = finding.get('title', '').lower()
        
        # Calculate derived metrics
        employees = company.get('employee_count') or 10
        engineers = max(1, int(employees * 0.3)) # Default assumption: 30% are engineers

        # CRITICAL secret exposed
        if severity == 'CRITICAL' and ('secret' in finding_type or 'secret' in title or finding_type == 'hardcoded secret'):
            min_usd = 50000.0
            max_usd = 1200000.0
            impact_type = "Data Breach Risk"
            one_liner = "Critical secret exposed; high risk of immediate breach and data exfiltration."
            
        # HIGH CVE (Assuming CVSS >= 7 maps to HIGH/CRITICAL in our severity)
        elif severity == 'HIGH' and ('cve' in title or 'vulnerability' in finding_type or finding_type == 'sca'):
            min_usd = 25000.0
            max_usd = 500000.0
            impact_type = "High Vulnerability Risk"
            one_liner = "High severity vulnerability detected; potential for system compromise."

        # MEDIUM CVE (CVSS 4-6.9)
        elif severity == 'MEDIUM' and ('cve' in title or 'vulnerability' in finding_type or finding_type == 'sca'):
            min_usd = 5000.0
            max_usd = 50000.0
            impact_type = "Medium Vulnerability Risk"
            one_liner = "Medium severity vulnerability; potential for partial system impact."

        # License violation
        elif 'license' in finding_type or 'license' in title:
            min_usd = 10000.0
            max_usd = 100000.0
            impact_type = "Legal Risk"
            one_liner = "License violation detected; potential for legal action or forced open-sourcing."

        # Performance bottleneck (This is a generic mapping as standard security tools don't often find pure 'bottlenecks' unless it's a specific SAST rule)
        elif 'performance' in finding_type or 'performance' in title or 'slow' in title:
            min_usd = 2000.0 * employees
            max_usd = 5000.0 * employees
            impact_type = "Operational Cost"
            one_liner = "Performance bottleneck identified; scales with employee operational delay."

        # Architecture debt (HIGH)
        elif severity == 'HIGH' and ('architecture' in title or 'debt' in title or 'sast' in finding_type):
            # Using SAST as a proxy for architecture debt if not otherwise categorized
            min_usd = 500.0 * engineers
            max_usd = 2000.0 * engineers
            impact_type = "Engineering Debt"
            one_liner = "High architecture debt; limits engineering velocity and feature delivery."
            
        else:
            # Fallback based purely on severity
            if severity == 'CRITICAL':
                min_usd = 20000.0
                max_usd = 100000.0
                impact_type = "Critical System Risk"
                one_liner = "Critical issue posing severe risk to system integrity."
            elif severity == 'HIGH':
                min_usd = 5000.0
                max_usd = 25000.0
                impact_type = "High System Risk"
                one_liner = "High severity issue posing significant risk."
            elif severity == 'MEDIUM':
                min_usd = 1000.0
                max_usd = 5000.0
                impact_type = "Medium System Risk"
                one_liner = "Medium severity issue."
            elif severity == 'LOW':
                min_usd = 100.0
                max_usd = 500.0
                impact_type = "Low System Risk"
                one_liner = "Low severity issue."

        return {
            "min_usd": min_usd,
            "max_usd": max_usd,
            "impact_type": impact_type,
            "one_liner": one_liner
        }

    def calculate_company_impact(self, findings: List[dict], company: dict) -> dict:
        total_min_usd = 0.0
        total_max_usd = 0.0
        critical_count = 0
        high_count = 0
        medium_count = 0
        
        scored_findings = []

        for finding in findings:
            if finding.get('is_false_positive'):
                continue
                
            impact = self.calculate_finding_impact(finding, company)
            total_min_usd += impact['min_usd']
            total_max_usd += impact['max_usd']
            
            severity = finding.get('verified_severity', finding.get('severity', '')).upper()
            if severity == 'CRITICAL':
                critical_count += 1
            elif severity == 'HIGH':
                high_count += 1
            elif severity == 'MEDIUM':
                medium_count += 1
                
            finding_with_impact = finding.copy()
            finding_with_impact['impact'] = impact
            scored_findings.append(finding_with_impact)

        # Sort top findings by max USD impact
        scored_findings.sort(key=lambda x: x['impact']['max_usd'], reverse=True)
        top_findings = scored_findings[:5] # Keep top 5

        # Generate a risk summary
        if total_max_usd > 1000000:
            risk_summary = f"Extreme risk exposure estimated up to ${total_max_usd:,.2f} due to {critical_count} critical vulnerabilities. Immediate remediation required."
        elif total_max_usd > 500000:
            risk_summary = f"High risk exposure estimated up to ${total_max_usd:,.2f}. Prioritize addressing {critical_count} critical and {high_count} high vulnerabilities."
        elif total_max_usd > 100000:
            risk_summary = f"Moderate risk exposure estimated up to ${total_max_usd:,.2f}. Contains {high_count} high and {medium_count} medium vulnerabilities."
        elif total_max_usd > 0:
            risk_summary = f"Low risk exposure estimated up to ${total_max_usd:,.2f}. Regular maintenance recommended."
        else:
            risk_summary = "No significant risk identified. Excellent security posture."

        return {
            "total_min_usd": total_min_usd,
            "total_max_usd": total_max_usd,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "top_findings": top_findings,
            "risk_summary": risk_summary
        }
