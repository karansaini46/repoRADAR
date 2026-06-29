from typing import List
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from autoscan.reports.pdf_utils import (
    Heading1Style, Heading2Style, BodyStyle, 
    TEXT_COLOR, BORDER_COLOR, ACCENT_COLOR
)

def build_recommendations(findings: List[dict]) -> List[Flowable]:
    """Build the recommendations and next steps section."""
    story = []
    
    story.append(Paragraph("Recommendations & Remediation Plan", Heading1Style))
    story.append(Spacer(1, 15))
    
    # Sort findings by severity weight (CRITICAL first), then by fix_hours
    severity_weight = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'INFO': 0}
    
    def get_sort_key(f):
        sev = f.get('verified_severity', f.get('severity', 'INFO')).upper()
        weight = severity_weight.get(sev, 0)
        hours = f.get('fix_hours_estimate', 0)
        return (weight, -hours) # High severity first, then higher hours first
        
    sorted_findings = sorted([f for f in findings if not f.get('is_false_positive')], key=get_sort_key, reverse=True)
    
    table_data = [["Priority", "Finding", "Est. Fix Hours"]]
    
    total_hours = 0
    for i, f in enumerate(sorted_findings[:10]): # Show top 10 actionable recommendations
        sev = f.get('verified_severity', f.get('severity', 'INFO')).upper()
        title = Paragraph(f.get('title', 'Unknown'), BodyStyle)
        hours = f.get('fix_hours_estimate', 0)
        total_hours += hours
        
        priority = f"P{i+1} ({sev})"
        table_data.append([priority, title, f"{hours}h"])
        
    if len(table_data) > 1:
        t = Table(table_data, colWidths=[80, 300, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#222222")),
            ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_COLOR),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, BORDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_COLOR),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        story.append(Paragraph(f"<b>Estimated Total Remediation Effort (Top 10):</b> {total_hours} hours", BodyStyle))
    else:
        story.append(Paragraph("No immediate remediation required.", BodyStyle))
        
    story.append(Spacer(1, 40))
    
    # CTA Section
    story.append(Paragraph("Next Steps", Heading2Style))
    story.append(Spacer(1, 10))
    cta_text = """
    Security is not a one-time activity. New vulnerabilities are discovered daily, and code changes can introduce new risks. 
    <b>Get this fixed and stay secure.</b> Purchase our continuous monitoring subscription to receive automated weekly 
    scans, instant alerts on new critical vulnerabilities, and direct access to our security engineering team.
    """
    
    cta_t = Table([[Paragraph(cta_text, BodyStyle)]], colWidths=['100%'])
    cta_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#1A3320")), # Dark green tint
        ('BOX', (0, 0), (-1, -1), 1, ACCENT_COLOR),
        ('PADDING', (0, 0), (-1, -1), 15),
    ]))
    
    story.append(cta_t)
    
    return story
