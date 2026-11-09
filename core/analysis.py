"""Deterministic document processing, extraction, and contextual comparisons."""
from __future__ import annotations
import io, re, unicodedata, os, csv, shutil, subprocess, tempfile
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import cv2
try:
    import fitz
except Exception:
    fitz = None
from pypdf import PdfReader

TESSERACT_CMD = os.getenv('TESSERACT_CMD')
SUPPORTED = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
PATTERNS = {
 'name': [r'(?:applicant|employee|account holder|full name|name)\s*[:\-]\s*([A-Z][A-Za-z .\'-]{2,60})'],
 'date_of_birth': [r'(?:date of birth|dob|birth date)\s*[:\-]\s*([\d./-]{6,12})'],
 'address': [r'(?:permanent address|residential address|address)\s*[:\-]\s*([^\n]{6,120})'],
 'salary': [r'(?:declared income|gross salary|monthly salary|salary(?!\s+credit))\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)'],
 'employer': [r'(?:employer|company)\s*[:\-]\s*([^\n]{2,70})'],
 'date': [r'(?:application date|invoice date|statement date|date)\s*[:\-]\s*([\d./-]{6,12})'],
 'account_holder': [r'(?:account holder|account name)\s*[:\-]\s*([A-Z][A-Za-z .\'-]{2,60})'],
 'id_number': [r'(?:id number|identity number|reference number|application reference)\s*[:\-]\s*([A-Z0-9-]{4,24})'],
 'amount': [r'(?:total amount|invoice total|closing balance|credit)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)'],
}
DOC_HINTS = {
 'Identity Proof': ('identity proof','identity number','date of birth','dob','id number'),
 'Address Proof': ('address proof','utility bill','residential address','permanent address'),
 'Application Form': ('application form','applicant','application reference','declared income'),
 'Bank Statement': ('bank statement','account holder','closing balance','transaction'),
 'Salary Slip': ('salary slip','gross salary','net pay','pay period'),
 'Employment Certificate': ('employment certificate','employed as','designation'),
 'Transaction Document': ('transaction request','transfer amount','beneficiary'),
 'Invoice': ('invoice','invoice number','tax amount','seller:'),
}

def validate_file(name: str, data: bytes, max_mb: int = 25) -> str:
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED: raise ValueError('Unsupported file type. Upload PDF, PNG, JPG or JPEG.')
    if not data or len(data) > max_mb * 1024 * 1024: raise ValueError(f'File is empty or exceeds {max_mb} MB.')
    valid = (ext == '.pdf' and data.startswith(b'%PDF')) or (ext == '.png' and data.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in ('.jpg','.jpeg') and data.startswith(b'\xff\xd8\xff'))
    if not valid: raise ValueError('File contents do not match the extension or are corrupted.')
    return SUPPORTED[ext]

def pages_from_bytes(data: bytes, name: str) -> list[tuple[int, Image.Image, str]]:
    ext = Path(name).suffix.lower(); pages=[]
    if ext == '.pdf':
        if fitz is not None:
            try:
                with fitz.open(stream=data, filetype='pdf') as pdf:
                    for i, page in enumerate(pdf):
                        text=page.get_text('text')
                        pix=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6), alpha=False)
                        img=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
                        pages.append((i+1,img,text))
                return pages
            except Exception:
                # A Windows application-control policy may block PyMuPDF's native renderer.
                # Continue with pure-Python PDF text extraction below.
                pages=[]
        reader=PdfReader(io.BytesIO(data),strict=False)
        for i, page in enumerate(reader.pages):
            text=page.extract_text() or ''
            img=Image.new('RGB',(900,1160),'white')
            from PIL import ImageDraw
            draw=ImageDraw.Draw(img)
            draw.text((35,35),f'PDF page {i+1} · text-only fallback preview',fill='#177b91')
            draw.text((35,75),'Page rendering is unavailable because the native PDF renderer could not load.',fill='#666666')
            y=125
            for line in text.splitlines():
                draw.text((35,y),line[:110],fill='#182b3d'); y+=22
                if y>1120: break
            img.info['docutrace_placeholder']=True
            pages.append((i+1,img,text))
    else: pages.append((1,Image.open(io.BytesIO(data)).convert('RGB'),''))
    return pages

def preprocess(image: Image.Image) -> Image.Image:
    image=ImageOps.grayscale(image)
    image.thumbnail((2400,2400))
    image=image.filter(ImageFilter.MedianFilter(3))
    return ImageEnhance.Contrast(image).enhance(1.4)

def ocr_page(image: Image.Image, embedded_text: str='') -> dict:
    if embedded_text.strip():
        return {'text': embedded_text, 'words': [], 'mean_confidence': None, 'method':'embedded PDF text'}
    try:
        executable=TESSERACT_CMD or shutil.which('tesseract')
        if not executable: raise FileNotFoundError('Tesseract executable not found. Install it or set TESSERACT_CMD in .env.')
        proc=preprocess(image)
        with tempfile.TemporaryDirectory(prefix='docutrace_') as temp:
            source=Path(temp)/'page.png'; proc.save(source)
            run=subprocess.run([executable,str(source),'stdout','--psm','6','tsv'],capture_output=True,text=True,check=True,timeout=90)
        words=[]; line_map={}
        for row in csv.DictReader(io.StringIO(run.stdout),delimiter='\t'):
            t=(row.get('text') or '').strip()
            if not t: continue
            try: conf=float(row.get('conf',-1))
            except ValueError: conf=-1
            words.append({'text':t,'confidence':conf,'bbox':[int(row[k]) for k in ('left','top','width','height')]})
            line_id=tuple(row.get(k,'') for k in ('page_num','block_num','par_num','line_num'))
            line_map.setdefault(line_id,[]).append(t)
        text='\n'.join(' '.join(parts) for parts in line_map.values())
        scores=[w['confidence'] for w in words if w['confidence']>=0]
        return {'text':text,'words':words,'mean_confidence':round(float(np.mean(scores)),1) if scores else None,'method':'Tesseract OCR'}
    except Exception as e:
        return {'text':'','words':[],'mean_confidence':None,'method':'unavailable','error':str(e)}

def classify(text: str, filename: str='') -> tuple[str,float]:
    low=text.lower(); scores={k:sum(1 for h in hints if h in low) for k,hints in DOC_HINTS.items()}
    best=max(scores,key=scores.get)
    if scores[best]==0: return 'Other / Unknown',0.0
    return best, min(.98,.55+.13*(scores[best]-1))

def extract_fields(text: str) -> dict[str,str]:
    out={}
    for field,patterns in PATTERNS.items():
        for pattern in patterns:
            match=re.search(pattern,text,re.I|re.M)
            if match:
                value=match.group(1).strip(' \t,;')
                out[field]=value
                break
    return out

def normalize(value: str) -> str:
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',value)

def compare_documents(docs: list[dict]) -> list[dict]:
    """Compare semantically related fields; values are from extracted fields."""
    findings=[]
    comparisons=[('name',None,'Identity discrepancy','High'),('address',None,'Address discrepancy','Medium'),('salary',None,'Financial discrepancy','Medium'),('date_of_birth',None,'Date inconsistency','High')]
    for key,_,category,severity in comparisons:
        values=[]
        for d in docs:
            value=d.get('fields',{}).get(key)
            if value: values.append((d,value))
        if len(values)<2: continue
        base_doc,base_value=values[0]
        differing=[]
        for doc,value in values[1:]:
            if normalize(value)==normalize(base_value): continue
            if key=='salary':
                try:
                    a=float(re.sub(r'[^\d.]','',base_value)); b=float(re.sub(r'[^\d.]','',value))
                    if abs(a-b)/max(a,b,1)<.05: continue
                except ValueError: pass
            differing.append((doc,value))
        if not differing: continue
        all_values={doc['name']:value for doc,value in values}
        summary='; '.join(f'{value} ({doc["name"]})' for doc,value in values)
        findings.append({'category':category,'severity':severity,'title':f'{key.replace("_"," ").title()} differs across documents','description':f'{key.replace("_"," ").title()} values found: {summary}. This may reflect extraction error or a genuine inconsistency and requires reviewer verification.','documents':[doc['id'] for doc,_ in values],'values':all_values,'fields':[key],'pages':[doc.get('page',1) for doc,_ in values],'method':'Deterministic normalized field comparison','confidence':'Comparison is exact after normalization; source extraction confidence varies','status':'Needs review'})
    return findings

def ela(image: Image.Image, quality: int=90) -> tuple[Image.Image, list[dict]]:
    buf=io.BytesIO(); image.convert('RGB').save(buf,format='JPEG',quality=quality)
    recompressed=Image.open(io.BytesIO(buf.getvalue())).convert('RGB')
    arr=np.asarray(image.convert('RGB')).astype(np.int16); comp=np.asarray(recompressed).astype(np.int16)
    diff=np.abs(arr-comp).astype(np.uint8)
    score=cv2.cvtColor(diff,cv2.COLOR_RGB2GRAY)
    scaled=cv2.normalize(score,None,0,255,cv2.NORM_MINMAX)
    heat=cv2.applyColorMap(scaled,cv2.COLORMAP_INFERNO)
    thr=max(30,int(np.percentile(score,98)))
    mask=(score>thr).astype('uint8')
    n, labels, stats, centroids=cv2.connectedComponentsWithStats(mask,8)
    regions=[]
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area>=max(10,int(score.size*.0002)):
            regions.append({'bbox':[int(x),int(y),int(w),int(h)],'area':int(area),'score':float(score[y:y+h,x:x+w].mean())})
    return Image.fromarray(cv2.cvtColor(heat,cv2.COLOR_BGR2RGB)), regions[:30]

def visual_difference(image: Image.Image) -> tuple[Image.Image,list[dict]]:
    arr=np.asarray(image.convert('RGB')); gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
    smooth=cv2.GaussianBlur(gray,(0,0),7); residual=cv2.absdiff(gray,smooth)
    _,mask=cv2.threshold(residual,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    heat=cv2.applyColorMap(residual,cv2.COLORMAP_JET)
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    regions=[]
    for c in sorted(contours,key=cv2.contourArea,reverse=True)[:20]:
        x,y,w,h=cv2.boundingRect(c)
        if cv2.contourArea(c)>max(40,arr.shape[0]*arr.shape[1]*.0001): regions.append({'bbox':[x,y,w,h],'area':int(cv2.contourArea(c))})
    return Image.fromarray(cv2.cvtColor(heat,cv2.COLOR_BGR2RGB)),regions
