import logging
import argparse
from sqlalchemy import select

from autoscan.shared.db.database import get_db, SessionLocal
from autoscan.shared.db.models import Company, Repository, Finding, Report
from autoscan.reports.builder import ReportBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_report_generation(company_id=None, limit=10, output_dir="/tmp/autoscan_reports"):
    """
    Pulls companies with status='impact_calculated', generates full and teaser PDFs,
    and updates the database.
    """
    builder = ReportBuilder(output_dir=output_dir)
    
    with SessionLocal() as db:
        query = select(Company).where(Company.status == 'impact_calculated')
        if company_id:
            query = query.where(Company.id == company_id)
        query = query.limit(limit)
        
        result = db.execute(query)
        companies = result.scalars().all()
        
        logger.info(f"Found {len(companies)} companies ready for report generation.")
        
        for company in companies:
            logger.info(f"Generating reports for company {company.name or company.github_org} (ID: {company.id})")
            try:
                # 1. Fetch Findings
                repos = db.query(Repository).filter(Repository.company_id == company.id).all()
                repo_ids = [repo.id for repo in repos]
                
                db_findings = []
                if repo_ids:
                    db_findings = db.query(Finding).filter(
                        Finding.repository_id.in_(repo_ids),
                        Finding.verified == True
                    ).all()
                    
                findings_dicts = []
                for dbf in db_findings:
                    findings_dicts.append({
                        "id": dbf.id,
                        "type": dbf.type,
                        "severity": dbf.severity,
                        "verified_severity": dbf.verified_severity,
                        "title": dbf.title,
                        "description": dbf.description,
                        "file_path": dbf.file_path,
                        "line_no": dbf.line_no,
                        "scanner_name": dbf.scanner_name,
                        "is_false_positive": dbf.is_false_positive,
                        "ai_explanation": dbf.ai_explanation,
                        "ai_recommendation": dbf.ai_recommendation,
                        "fix_hours_estimate": dbf.fix_hours_estimate
                    })
                    
                company_dict = {
                    "id": company.id,
                    "name": company.name,
                    "github_org": company.github_org,
                    "report_tier": company.report_tier,
                    "estimated_risk_min_usd": company.estimated_risk_min_usd,
                    "estimated_risk_max_usd": company.estimated_risk_max_usd
                }
                
                # We need to construct the impact dict. We can either re-calculate or just derive basic counts
                impact_dict = {
                    "risk_summary": "Security findings detected.",
                    "total_min_usd": company.estimated_risk_min_usd,
                    "total_max_usd": company.estimated_risk_max_usd,
                    "critical_count": sum(1 for f in findings_dicts if f.get('verified_severity') == 'CRITICAL' and not f.get('is_false_positive')),
                    "high_count": sum(1 for f in findings_dicts if f.get('verified_severity') == 'HIGH' and not f.get('is_false_positive')),
                    "medium_count": sum(1 for f in findings_dicts if f.get('verified_severity') == 'MEDIUM' and not f.get('is_false_positive'))
                }
                
                # Create a generic risk summary based on total max usd for the report text
                if impact_dict["total_max_usd"] and impact_dict["total_max_usd"] > 1000000:
                    impact_dict["risk_summary"] = f"Extreme risk exposure estimated up to ${impact_dict['total_max_usd']:,.2f}."
                elif impact_dict["total_max_usd"] and impact_dict["total_max_usd"] > 100000:
                    impact_dict["risk_summary"] = f"Moderate risk exposure estimated up to ${impact_dict['total_max_usd']:,.2f}."

                # 2. Generate PDFs
                full_path = builder.build_full_report(company_dict, impact_dict, findings_dicts)
                teaser_path = builder.build_teaser_report(company_dict, impact_dict)
                
                # 3. Save to DB
                report = Report(
                    company_id=company.id,
                    full_report_path=str(full_path),
                    teaser_report_path=str(teaser_path)
                )
                db.add(report)
                
                company.status = 'report_ready'
                db.commit()
                
                logger.info(f"Successfully generated reports for {company.name or company.github_org}.")
                
            except Exception as e:
                logger.error(f"Failed to generate reports for company {company.id}: {e}")
                db.rollback()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Report Generation Pipeline")
    parser.add_argument("--company-id", type=int, help="Generate report for a specific company ID")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of companies to process")
    parser.add_argument("--output-dir", type=str, default="/tmp/autoscan_reports", help="Output directory for PDFs")
    
    args = parser.parse_args()
    
    logger.info("Starting Report Generation pipeline...")
    run_report_generation(company_id=args.company_id, limit=args.limit, output_dir=args.output_dir)
    logger.info("Report Generation pipeline finished.")
