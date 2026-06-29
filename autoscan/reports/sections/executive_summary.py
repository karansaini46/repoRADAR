from typing import List
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.platypus import PageBreak

from autoscan.reports.pdf_utils import Heading1Style, BodyStyle, TEXT_COLOR, BORDER_COLOR, CARD_BG

def build_executive_summary(impact: dict, company: dict) -> List[Flowable]:
    """Build the executive summary section."""
    story = []
    
    story.append(Paragraph("Executive Summary", Heading1Style))
    story.append(Spacer(1, 10))
    
    risk_summary = impact.get('risk_summary', 'No significant risk identified.')
    
    # We could replace this with a dynamic API call in the future.
    paragraph_text = f"""Based on our automated security analysis of your organization's codebase, 
    we have identified several security findings that carry potential financial and operational risks. 
    <b>{risk_summary}</b> This report outlines the technical details and business impact of the top identified issues."""
    
    story.append(Paragraph(paragraph_text, BodyStyle))
    story.append(Spacer(1, 20))
    
    # Risk Overview Table
    # Severity Level | Count | Est. Cost Range
    
    # Re-calculate costs per severity from top findings to give a breakdown, or just use general estimates.
    # We will use general estimates or aggregate from impact if available.
    # Since impact dict doesn't give us broken down costs per severity natively yet, we will just show counts.
    
    data = [
        ["Severity Level", "Count", "Est. Cost Range"]
    ]
    
    # Approximate breakdown for the table
    c_count = impact.get('critical_count', 0)
    h_count = impact.get('high_count', 0)
    m_count = impact.get('medium_count', 0)
    
    # We use some generic ranges for the summary table if we don't have exact ones per severity easily available
    c_cost = "$50k - $1.2m" if c_count > 0 else "$0"
    h_cost = "$25k - $500k" if h_count > 0 else "$0"
    m_cost = "$5k - $50k" if m_count > 0 else "$0"
    
    data.append(["CRITICAL", str(c_count), c_cost])
    data.append(["HIGH", str(h_count), h_cost])
    data.append(["MEDIUM", str(m_count), m_cost])
    
    t = Table(data, colWidths=[150, 100, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#222222")),
        ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_COLOR),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor("#FF0000")), # CRITICAL
        ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor("#FF4D4D")), # HIGH
        ('TEXTCOLOR', (0, 3), (0, 3), colors.HexColor("#FFB800")), # MEDIUM
        
        ('TEXTCOLOR', (1, 1), (-1, -1), TEXT_COLOR),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('BACKGROUND', (0, 1), (-1, -1), CARD_BG),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(t)
    story.append(PageBreak())
    
    return story
