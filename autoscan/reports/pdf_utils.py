from typing import List
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, TableStyle

# Theme Colors
BG_COLOR = colors.HexColor("#0D0D0D")
TEXT_COLOR = colors.HexColor("#E0E0E0")
ACCENT_COLOR = colors.HexColor("#00FF88")
CRITICAL_COLOR = colors.HexColor("#FF0000")
HIGH_COLOR = colors.HexColor("#FF4D4D")
MEDIUM_COLOR = colors.HexColor("#FFB800")
LOW_COLOR = colors.HexColor("#00BFFF")
INFO_COLOR = colors.HexColor("#A0A0A0")
CARD_BG = colors.HexColor("#1A1A1A")
BORDER_COLOR = colors.HexColor("#333333")

# Shared Styles
styles = getSampleStyleSheet()

TitleStyle = ParagraphStyle(
    'TitleStyle',
    parent=styles['Title'],
    textColor=ACCENT_COLOR,
    fontSize=24,
    spaceAfter=20,
    fontName='Helvetica-Bold'
)

Heading1Style = ParagraphStyle(
    'Heading1Style',
    parent=styles['Heading1'],
    textColor=ACCENT_COLOR,
    fontSize=18,
    spaceBefore=15,
    spaceAfter=10,
    fontName='Helvetica-Bold'
)

Heading2Style = ParagraphStyle(
    'Heading2Style',
    parent=styles['Heading2'],
    textColor=TEXT_COLOR,
    fontSize=14,
    spaceBefore=10,
    spaceAfter=8,
    fontName='Helvetica-Bold'
)

BodyStyle = ParagraphStyle(
    'BodyStyle',
    parent=styles['Normal'],
    textColor=TEXT_COLOR,
    fontSize=10,
    leading=14,
    fontName='Helvetica'
)

MonospaceStyle = ParagraphStyle(
    'MonospaceStyle',
    parent=styles['Normal'],
    textColor=ACCENT_COLOR,
    fontSize=9,
    leading=12,
    fontName='Courier'
)

def dark_page_background(canvas, doc):
    """Draw a dark background on every page."""
    canvas.saveState()
    canvas.setFillColor(BG_COLOR)
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1)
    canvas.restoreState()

def code_block(lines: List[str]) -> Table:
    """Create a dark code block table."""
    data = [[line] for line in lines]
    
    t = Table(data, colWidths=['100%'])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#050505")),
        ('TEXTCOLOR', (0, 0), (-1, -1), ACCENT_COLOR),
        ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
    ]))
    return t

def severity_badge(severity: str) -> Table:
    """Return a styled colored badge for the severity."""
    sev = severity.upper()
    
    color_map = {
        'CRITICAL': CRITICAL_COLOR,
        'HIGH': HIGH_COLOR,
        'MEDIUM': MEDIUM_COLOR,
        'LOW': LOW_COLOR,
        'INFO': INFO_COLOR
    }
    
    bg_color = color_map.get(sev, INFO_COLOR)
    
    data = [[sev]]
    t = Table(data, colWidths=[60], rowHeights=[20])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOX', (0, 0), (-1, -1), 1, bg_color),
    ]))
    return t
