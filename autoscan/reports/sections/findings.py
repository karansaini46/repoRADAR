from typing import List
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib import colors

from autoscan.reports.pdf_utils import (
    Heading1Style, Heading2Style, BodyStyle, 
    TEXT_COLOR, BORDER_COLOR, CARD_BG, ACCENT_COLOR,
    severity_badge, code_block
)

def build_findings_section(findings: List[dict], severity_filter=None) -> List[Flowable]:
    """Build the findings section."""
    story = []
    
    story.append(Paragraph("Detailed Findings", Heading1Style))
    story.append(Spacer(1, 15))
    
    filtered_findings = findings
    if severity_filter:
        filtered_findings = [f for f in findings if f.get('verified_severity', f.get('severity', '')).upper() in severity_filter]
        
    if not filtered_findings:
        story.append(Paragraph("No significant findings reported.", BodyStyle))
        return story

    # CRITICAL/HIGH findings get full cards
    critical_high = [f for f in filtered_findings if f.get('verified_severity', f.get('severity', '')).upper() in ['CRITICAL', 'HIGH']]
    
    # MEDIUM/LOW get table rows
    medium_low = [f for f in filtered_findings if f.get('verified_severity', f.get('severity', '')).upper() in ['MEDIUM', 'LOW']]
    
    for f in critical_high:
        card = []
        sev = f.get('verified_severity', f.get('severity', 'UNKNOWN')).upper()
        
        # Header: Badge + Title
        badge = severity_badge(sev)
        title = Paragraph(f.get('title', 'Unknown Finding'), Heading2Style)
        
        header_table = Table([[badge, title]], colWidths=[70, 380])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        card.append(header_table)
        card.append(Spacer(1, 5))
        
        # Metadata: File Path, Scanner
        meta_text = f"<b>Location:</b> {f.get('file_path', 'Unknown')}:{f.get('line_no', '')} | <b>Detected by:</b> {f.get('scanner_name', 'Unknown')}"
        card.append(Paragraph(meta_text, BodyStyle))
        card.append(Spacer(1, 10))
        
        # Explanation
        explanation = f.get('ai_explanation') or f.get('description', '')
        # Replace newlines with <br/> for Paragraph compatibility
        explanation = str(explanation).replace('\n', '<br/>')
        card.append(Paragraph(explanation, BodyStyle))
        card.append(Spacer(1, 10))
        
        # Code Snippet (Simulated here. We don't have the raw lines in the dict easily, but we'll try to use a placeholder or extract from raw if available)
        # In a real scenario we might pass the snippet text. For now, a placeholder if not present.
        card.append(Paragraph("<b>Code Context:</b>", BodyStyle))
        snippet_lines = ["// Code snippet unavailable in summary view."]
        card.append(code_block(snippet_lines))
        card.append(Spacer(1, 10))
        
        # Recommendation
        rec = f.get('ai_recommendation') or "No specific recommendation provided."
        rec = str(rec).replace('\n', '<br/>')
        card.append(Paragraph(f"<b>Recommendation:</b> {rec}", BodyStyle))
        card.append(Spacer(1, 10))
        
        # Wrap card in a KeepTogether to avoid breaking across pages inside a single finding if possible
        story.append(KeepTogether(card))
        story.append(Spacer(1, 20))
        
    if medium_low:
        story.append(Paragraph("Other Findings", Heading1Style))
        story.append(Spacer(1, 10))
        
        table_data = [["Severity", "Finding", "Location"]]
        
        for f in medium_low:
            sev = f.get('verified_severity', f.get('severity', 'UNKNOWN')).upper()
            title = Paragraph(f.get('title', 'Unknown'), BodyStyle)
            loc_str = f"{f.get('file_path', 'Unknown')}:{f.get('line_no', '')}"
            loc = Paragraph(loc_str, BodyStyle)
            table_data.append([sev, title, loc])
            
        t = Table(table_data, colWidths=[80, 250, 150])
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
        
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
        
    return story
