from typing import List
import datetime
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from autoscan.reports.pdf_utils import TitleStyle, BodyStyle, ACCENT_COLOR, TEXT_COLOR, BORDER_COLOR

def build_cover(company: dict, impact: dict) -> List[Flowable]:
    """Build the cover page for the report."""
    story = []
    
    # Push down from top
    story.append(Spacer(1, 150))
    
    # Logo / Title
    story.append(Paragraph("AutoScan Security Report", TitleStyle))
    story.append(Spacer(1, 30))
    
    # Company Name
    comp_name = company.get('name') or company.get('github_org') or "Unknown Company"
    story.append(Paragraph(f"<b>Prepared for:</b> {comp_name}", BodyStyle))
    
    # Date
    date_str = datetime.datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"<b>Date:</b> {date_str}", BodyStyle))
    story.append(Spacer(1, 50))
    
    # Risk Tier Badge and Overall Risk Range
    tier = company.get('report_tier', 'Standard').upper()
    min_usd = company.get('estimated_risk_min_usd', 0)
    max_usd = company.get('estimated_risk_max_usd', 0)
    
    summary_data = [
        ["Risk Tier:", tier],
        ["Estimated Financial Risk:", f"${min_usd:,.0f} - ${max_usd:,.0f}"]
    ]
    
    t = Table(summary_data, colWidths=[150, 250])
    t.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (1, 0), (1, 0), ACCENT_COLOR), # Highlight Tier
    ]))
    
    story.append(t)
    story.append(Spacer(1, 40))
    
    # Critical / High / Medium Counts
    crit_cnt = impact.get('critical_count', 0)
    high_cnt = impact.get('high_count', 0)
    med_cnt = impact.get('medium_count', 0)
    
    counts_data = [
        ["CRITICAL", "HIGH", "MEDIUM"],
        [str(crit_cnt), str(high_cnt), str(med_cnt)]
    ]
    
    counts_t = Table(counts_data, colWidths=[100, 100, 100])
    counts_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#222222")),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor("#FF0000")), # CRITICAL
        ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor("#FF4D4D")), # HIGH
        ('TEXTCOLOR', (2, 0), (2, 0), colors.HexColor("#FFB800")), # MEDIUM
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('TEXTCOLOR', (0, 1), (-1, 1), TEXT_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, BORDER_COLOR),
    ]))
    
    story.append(counts_t)
    
    # Page Break after cover
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
    
    return story
