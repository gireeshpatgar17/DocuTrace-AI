from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak

def make_report(investigation,documents,findings)->bytes:
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=letter,rightMargin=45,leftMargin=45,topMargin=50,bottomMargin=45)
    styles=getSampleStyleSheet(); story=[Paragraph('DocuTrace AI',styles['Title']),Paragraph('Investigation Review Dossier',styles['Heading2']),Spacer(1,14)]
    story += [Paragraph(f'<b>Investigation:</b> {investigation.title}',styles['BodyText']),Paragraph(f'<b>ID:</b> {investigation.id}',styles['BodyText']),Paragraph(f'<b>Category:</b> {investigation.category}',styles['BodyText']),Paragraph(f'<b>Created:</b> {investigation.created_at}',styles['BodyText']),Spacer(1,18),Paragraph('Documents processed',styles['Heading2'])]
    rows=[['Filename','Classified as','Pages','SHA-256']]+[[d.name,d.doc_type,str(d.page_count),d.sha256[:16]+'…'] for d in documents]
    table=Table(rows,colWidths=[150,120,45,150],repeatRows=1); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#18304b')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8)])); story += [table,Spacer(1,18),Paragraph('Findings for human review',styles['Heading2'])]
    if findings:
        for f in findings:
            story += [Paragraph(f'<b>{f.severity} · {f.category}: {f.title}</b>',styles['Heading3']),Paragraph(f.description,styles['BodyText']),Paragraph(f'<i>Status: {f.status}. Reviewer note: {f.reviewer_note or "None"}</i>',styles['BodyText']),Spacer(1,9)]
    else: story.append(Paragraph('No cross-document discrepancies were detected from available extracted fields.',styles['BodyText']))
    story += [Spacer(1,15),Paragraph('Method and limitations',styles['Heading2']),Paragraph('This dossier reports automated text extraction, rule-based comparisons and heuristic image observations. OCR can be incorrect; visual anomalies are not proof of manipulation; absence of a finding does not establish authenticity. Findings require qualified human review. Original uploaded evidence is retained separately with recorded SHA-256 hashes. This local audit trail is not tamper-proof.',styles['BodyText'])]
    def footer(canvas,document):
        canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.grey); canvas.drawString(45,25,'DocuTrace AI · Human review required'); canvas.drawRightString(565,25,f'Page {document.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer); return buf.getvalue()
