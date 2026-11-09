from pathlib import Path
from reportlab.pdfgen import canvas
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]/'data'/'demo'
SETS={
'clean':[
('application.pdf',['APPLICATION FORM','Applicant: Maya Rao','Date of birth: 02/04/1990','Address: 14 Lake Road, Pune 411001','Declared income: INR 75,000','Application reference: CLN-1042']),
('identity.pdf',['IDENTITY PROOF','Full name: Maya Rao','Date of birth: 02/04/1990','ID number: ID-482019']),
('address.pdf',['ADDRESS PROOF','Full name: Maya Rao','Address: 14 Lake Road, Pune 411001','Document date: 03/10/2026']),
('salary.pdf',['SALARY SLIP','Employee name: Maya Rao','Employer: Northstar Analytics','Gross salary: INR 75,000','Net pay: INR 68,500']),
('bank.pdf',['BANK STATEMENT','Account holder: Maya Rao','Salary credit: INR 68,500','Closing balance: INR 120,400'])],
'contextual_discrepancy':[
('application.pdf',['APPLICATION FORM','Applicant: Maya Rao','Date of birth: 02/04/1990','Address: 14 Lake Road, Pune 411001','Declared income: INR 75,000']),
('identity.pdf',['IDENTITY PROOF','Full name: Maya Rao','Date of birth: 03/04/1990','ID number: ID-482019']),
('address.pdf',['ADDRESS PROOF','Full name: M. Rao','Address: 88 Hill Street, Mumbai 400001']),
('salary.pdf',['SALARY SLIP','Employee name: Maya Rao','Employer: Northstar Analytics','Gross salary: INR 92,000']),
('bank.pdf',['BANK STATEMENT','Account holder: Rohan Shah','Salary credit: INR 62,000'])]}

def pdf(path,lines):
    page=canvas.Canvas(str(path),pagesize=(595,842))
    page.setFillColorRGB(.2,.55,.65); page.setFont('Helvetica',9); page.drawString(55,777,'DOCUTRACE AI - SYNTHETIC DEMONSTRATION')
    page.setStrokeColorRGB(.5,.6,.7); page.line(55,764,540,764)
    for i,line in enumerate(lines):
        page.setFillColorRGB(.08,.14,.22); page.setFont('Helvetica-Bold' if i==0 else 'Helvetica',17 if i==0 else 13); page.drawString(60,717-i*38,line)
    page.setFillColorRGB(.45,.45,.45); page.setFont('Helvetica',8); page.drawString(55,42,'FICTIONAL DATA - NOT A REAL PERSON OR FINANCIAL RECORD')
    page.save()

for scenario, docs in SETS.items():
    folder=ROOT/scenario; folder.mkdir(parents=True,exist_ok=True)
    for name,lines in docs: pdf(folder/name,lines)

folder=ROOT/'visual_manipulation'; folder.mkdir(parents=True,exist_ok=True)
img=Image.new('RGB',(1200,700),'white'); draw=ImageDraw.Draw(img)
draw.text((70,60),'DOCUTRACE AI · SYNTHETIC SALARY SLIP',fill='#167e96')
draw.line((70,100,1120,100),fill='#667788',width=2)
for y,text in [(170,'Employee name: Maya Rao'),(250,'Employer: Northstar Analytics'),(330,'Gross salary: INR 75,000'),(410,'Net pay: INR 68,500')]: draw.text((90,y),text,fill='#182b3d')
img.save(folder/'original.png')
edited=img.copy(); d=ImageDraw.Draw(edited); d.rectangle((375,320,700,360),fill='white'); d.text((390,330),'Gross salary: INR 95,000',fill='#182b3d'); edited.save(folder/'modified.png')
print(f'Generated synthetic demo data under {ROOT}')
