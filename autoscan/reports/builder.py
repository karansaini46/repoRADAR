import os
import datetime
from pathlib import Path
from typing import List

from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import letter

from autoscan.reports.pdf_utils import dark_page_background
from autoscan.reports.sections.cover import build_cover
from autoscan.reports.sections.executive_summary import build_executive_summary
from autoscan.reports.sections.findings import build_findings_section
from autoscan.reports.sections.recommendations import build_recommendations

class ReportBuilder:
    def __init__(self, output_dir: str = '/tmp/autoscan_reports'):
        self.output_dir = Path(output_dir)
        
    def _ensure_dir(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        
    def _create_doc(self, path: Path) -> SimpleDocTemplate:
        self._ensure_dir(path)
        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        return doc
        
    def _build(self, path: Path, story: List):
        doc = self._create_doc(path)
        # Apply dark background to all pages
        doc.build(story, onFirstPage=dark_page_background, onLaterPages=dark_page_background)

    def build_full_report(self, company: dict, impact: dict, findings: List[dict]) -> Path:
        """Build the full comprehensive report."""
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        comp_id = company.get('id', 'unknown')
        output_path = self.output_dir / str(comp_id) / f"full_{date_str}.pdf"
        
        story = []
        story.extend(build_cover(company, impact))
        story.extend(build_executive_summary(impact, company))
        story.extend(build_findings_section(findings, severity_filter=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']))
        story.extend(build_recommendations(findings))
        
        self._build(output_path, story)
        return output_path

    def build_teaser_report(self, company: dict, impact: dict) -> Path:
        """Build the teaser report (cover + exec summary only)."""
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        comp_id = company.get('id', 'unknown')
        output_path = self.output_dir / str(comp_id) / f"teaser_{date_str}.pdf"
        
        story = []
        story.extend(build_cover(company, impact))
        story.extend(build_executive_summary(impact, company))
        
        self._build(output_path, story)
        return output_path
