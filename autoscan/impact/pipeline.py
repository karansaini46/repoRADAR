import logging
import argparse
from sqlalchemy import select

from autoscan.shared.db.database import get_db, SessionLocal
from autoscan.shared.db.models import Company, Repository, Finding
from autoscan.impact.calculators import ImpactCalculator
from autoscan.impact.pricing import determine_report_price

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_impact_calculation(company_id=None, limit=20):
    """
    Pulls companies, calculates their overall risk impact, determines report pricing,
    and updates the database.
    
    Note: A company is ready for impact calculation if its repositories have been 'verified'.
    We will just pull all companies for now, but in a real flow you might filter based on
    a specific state machine for the Company model (e.g. status='verified' or 'cloned').
    We'll assume 'NEW' or 'QUALIFIED' or whatever its last state was before scanning.
    Let's process any company that hasn't had impact calculated yet (where impact_score is null).
    """
    
    calculator = ImpactCalculator()
    
    with SessionLocal() as db:
        # Finding companies that haven't had impact calculated yet
        query = select(Company).where(Company.status != 'impact_calculated')
        if company_id:
            query = query.where(Company.id == company_id)
        query = query.limit(limit)
        
        result = db.execute(query)
        companies = result.scalars().all()
        
        logger.info(f"Found {len(companies)} companies to calculate impact for.")
        
        for company in companies:
            logger.info(f"Calculating impact for company {company.name or company.github_org} (ID: {company.id})")
            try:
                # 1. Fetch all verified findings for this company's repositories
                repos = db.query(Repository).filter(Repository.company_id == company.id).all()
                repo_ids = [repo.id for repo in repos]
                
                if not repo_ids:
                    logger.info(f"Company {company.id} has no repositories.")
                    continue
                    
                db_findings = db.query(Finding).filter(
                    Finding.repository_id.in_(repo_ids),
                    Finding.verified == True,
                    Finding.is_false_positive == False
                ).all()
                
                # Convert DB models to dicts for the calculator
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
                        "is_false_positive": dbf.is_false_positive
                    })
                
                company_dict = {
                    "id": company.id,
                    "employee_count": company.employee_count,
                    "qualification_score": company.qualification_score,
                    "enrichment_score": company.enrichment_score
                }
                
                # 2. Run Impact Calculation
                impact_result = calculator.calculate_company_impact(findings_dicts, company_dict)
                
                # 3. Determine Pricing
                pricing_result = determine_report_price(impact_result, company_dict)
                
                # 4. Update Database
                company.estimated_risk_min_usd = impact_result['total_min_usd']
                company.estimated_risk_max_usd = impact_result['total_max_usd']
                
                # Impact score could be a normalized score, let's just use total max risk as a raw score
                # or a logarithmic scale. We'll store total_max_usd / 1000 for a simplified score.
                company.impact_score = impact_result['total_max_usd'] / 1000.0
                
                company.report_price_cents = pricing_result['price_cents']
                company.report_tier = pricing_result['tier']
                company.status = 'impact_calculated'
                
                db.commit()
                logger.info(f"Impact calculated for {company.name or company.github_org}. Tier: {pricing_result['tier']}, Max Risk: ${impact_result['total_max_usd']:,.2f}")
                
            except Exception as e:
                logger.error(f"Failed to calculate impact for company {company.id}: {e}")
                db.rollback()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Impact Calculator Pipeline")
    parser.add_argument("--company-id", type=int, help="Calculate impact for a specific company ID")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of companies to process")
    
    args = parser.parse_args()
    
    logger.info("Starting Impact Calculation pipeline...")
    run_impact_calculation(company_id=args.company_id, limit=args.limit)
    logger.info("Impact Calculation pipeline finished.")
