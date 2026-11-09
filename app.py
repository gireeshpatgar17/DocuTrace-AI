from __future__ import annotations
import hashlib, io, uuid
from pathlib import Path
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from config.settings import ROOT, DATA, MAX_UPLOAD_MB, ELA_QUALITY
from core.analysis import validate_file,pages_from_bytes,ocr_page,classify,extract_fields,compare_documents,ela,visual_difference
from models.database import Session, Investigation, Document, Finding, audit
load_dotenv(ROOT/'.env')

st.set_page_config(page_title='DocuTrace AI | Document investigation',page_icon='🔎',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
.stApp{background:#08111f;color:#e7edf7;font-family:'DM Sans',sans-serif}.block-container{padding-top:1.4rem;max-width:1500px}
[data-testid="stSidebar"]{background:#0c1728;border-right:1px solid #1d2c42}.hero{padding:28px 30px;border:1px solid #20324a;border-radius:18px;background:linear-gradient(115deg,#10223a,#0e1828 65%,#13283a);margin-bottom:22px}.hero h1{font:700 34px 'Space Grotesk';margin:3px 0;color:#f1f6ff}.eyebrow{color:#46c5dd;letter-spacing:.12em;font-size:11px;font-weight:700}.muted{color:#91a2ba}.metric{padding:19px;border-radius:14px;background:#101d30;border:1px solid #1f3048}.metric .v{font:700 27px 'Space Grotesk';color:#f2f6fd}.metric .l{color:#8fa2bb;font-size:12px}.stButton button[kind="primary"]{background:#137b98;border-color:#198ba6}.finding{padding:16px 18px;border:1px solid #24364e;border-left:4px solid #e8a441;background:#0f1a2a;border-radius:12px;margin:8px 0}
</style>''',unsafe_allow_html=True)
if 'page' not in st.session_state: st.session_state.page='Dashboard'
if 'active_id' not in st.session_state: st.session_state.active_id=None
with Session() as db:
    st.sidebar.markdown('## 🔎 DocuTrace AI')
    st.sidebar.caption('Beyond OCR. Towards Intelligent Document Investigation.')
    pages=['Dashboard','New Investigation','Investigations','Document Analysis','Visual Forensics','Contextual Intelligence','Findings & Evidence','Investigation Reports','Settings','About DocuTrace AI']
    st.session_state.page=st.sidebar.radio('Workspace',pages,index=pages.index(st.session_state.page))
    investigations=db.query(Investigation).order_by(Investigation.created_at.desc()).all()
    if investigations:
        options={f'{x.title} · {x.id[:8]}':x.id for x in investigations}
        labels=list(options); current=next((k for k,v in options.items() if v==st.session_state.active_id),labels[0])
        st.session_state.active_id=options[st.sidebar.selectbox('Active investigation',labels,index=labels.index(current))]
    else: st.session_state.active_id=None
    active=db.get(Investigation,st.session_state.active_id) if st.session_state.active_id else None
    docs=active.documents if active else []; findings=active.findings if active else []
    page=st.session_state.page
    if page=='Dashboard':
        st.markdown('<div class="hero"><div class="eyebrow">DOCUMENT INTELLIGENCE · FORENSICS · EVIDENCE</div><h1>Investigate with context.</h1><div class="muted">A traceable workspace for reviewing document consistency and visual observations.</div></div>',unsafe_allow_html=True)
        all_docs=db.query(Document).all(); all_find=db.query(Finding).all()
        cols=st.columns(4)
        for c,label,val in zip(cols,['Investigations','Documents processed','Findings for review','High priority'],[db.query(Investigation).count(),len(all_docs),len(all_find),sum(f.severity in ('High','Critical') for f in all_find)]):
            c.markdown(f'<div class="metric"><div class="v">{val}</div><div class="l">{label}</div></div>',unsafe_allow_html=True)
        st.write('')
        left,right=st.columns([1.2,1])
        with left:
            st.subheader('Recent investigations')
            if investigations:
                for item in investigations[:8]:
                    st.markdown(f"**{item.title}** · {item.category} · {len(item.documents)} docs · {len(item.findings)} findings · {item.created_at:%Y-%m-%d %H:%M}")
            else: st.info('No investigations yet. Create one to begin a review.')
        with right:
            st.subheader('Finding categories')
            if all_find:
                categories=sorted({f.category for f in all_find})
                severities=sorted({f.severity for f in all_find})
                chart=go.Figure()
                for severity in severities:
                    chart.add_bar(name=severity,x=categories,y=[sum(f.category==category and f.severity==severity for f in all_find) for category in categories])
                chart.update_layout(template='plotly_dark',barmode='stack',xaxis_title='Category',yaxis_title='Findings')
                st.plotly_chart(chart,use_container_width=True)
            else: st.caption('Category chart will populate from processed investigations.')
    elif page=='New Investigation':
        st.header('New investigation')
        with st.form('new_inv'):
            title=st.text_input('Investigation title',placeholder='Loan Application Verification'); category=st.selectbox('Category',['Loan application','Identity verification','Financial review','General']); description=st.text_area('Description')
            files=st.file_uploader('Upload related documents',type=['pdf','png','jpg','jpeg'],accept_multiple_files=True,help=f'Maximum {MAX_UPLOAD_MB} MB per file. Original bytes are preserved.')
            submitted=st.form_submit_button('Create and process',type='primary')
        if submitted:
            if not title.strip(): st.error('Enter a title before processing.')
            else:
                inv_id=str(uuid.uuid4()); inv=Investigation(id=inv_id,title=title.strip(),category=category,description=description); db.add(inv); db.commit(); audit(db,inv_id,'Investigation created',title)
                progress=st.progress(0); status=st.empty(); accepted=[]
                for n,up in enumerate(files or []):
                    try:
                        data=up.getvalue(); mime=validate_file(up.name,data,MAX_UPLOAD_MB); doc_id=str(uuid.uuid4()); digest=hashlib.sha256(data).hexdigest()
                        path=DATA/'uploads'/inv_id/f'{doc_id}{Path(up.name).suffix.lower()}'; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
                        pages=pages_from_bytes(data,up.name); full=[]; all_fields={}; first_ocr={}
                        for pno,img,embedded in pages:
                            res=ocr_page(img,embedded); full.append(res['text']);
                            if pno==1: first_ocr=res
                            for k,v in extract_fields(res['text']).items(): all_fields.setdefault(k,v)
                        text='\n'.join(full); dtype,conf=classify(text,up.name)
                        doc=Document(id=doc_id,investigation_id=inv_id,name=up.name,path=str(path),sha256=digest,mime_type=mime,text=text,fields=all_fields,doc_type=dtype,classification_confidence=conf,page_count=len(pages),status='Processed' if text or first_ocr.get('method')=='embedded PDF text' else 'OCR unavailable')
                        db.add(doc); db.commit(); audit(db,inv_id,'Document processed',f'{up.name}: {dtype}; {len(pages)} page(s)'); accepted.append(doc)
                    except Exception as e: st.warning(f'{up.name}: {e}')
                    progress.progress((n+1)/max(len(files or []),1)); status.write(f'Processed {n+1} of {len(files or [])} documents')
                if accepted:
                    current=db.query(Document).filter_by(investigation_id=inv_id).all()
                    for item in compare_documents([{'id':d.id,'name':d.name,'fields':d.fields,'page':1} for d in current]):
                        db.add(Finding(id=str(uuid.uuid4()),investigation_id=inv_id,category=item['category'],severity=item['severity'],title=item['title'],description=item['description'],evidence=item))
                    db.commit(); audit(db,inv_id,'Analysis completed',f'{len(current)} document(s); contextual comparisons generated')
                st.session_state.active_id=inv_id; st.success(f'Investigation created. {len(accepted)} document(s) processed.'); st.rerun()
    elif page=='Investigations':
        st.header('Investigations')
        if investigations:
            for inv in investigations:
                with st.expander(f'{inv.title} · {inv.id[:8]} · {inv.status}'):
                    st.write(inv.description or 'No description'); st.write(f'{len(inv.documents)} documents · {len(inv.findings)} findings · created {inv.created_at:%Y-%m-%d %H:%M UTC}')
                    if st.button('Open investigation',key=f'open{inv.id}'): st.session_state.active_id=inv.id
                    with st.form(f'delete{inv.id}'):
                        confirm=st.checkbox('Confirm permanent deletion of this investigation and stored files')
                        if st.form_submit_button('Delete investigation') and confirm:
                            for doc in inv.documents:
                                try: Path(doc.path).unlink(missing_ok=True)
                                except OSError: pass
                            audit_id=inv.id; db.delete(inv); db.commit()
                            folder=DATA/'uploads'/audit_id
                            if folder.exists():
                                import shutil; shutil.rmtree(folder,ignore_errors=True)
                            st.rerun()
        else: st.info('No investigations have been created yet.')
    elif page=='Document Analysis':
        st.header('Document analysis')
        if not active: st.info('Create or select an investigation first.')
        elif not docs: st.info('This investigation has no documents.')
        else:
            selected=st.selectbox('Document',[f'{d.name} · {d.id[:8]}' for d in docs]); doc=docs[[f'{d.name} · {d.id[:8]}' for d in docs].index(selected)]
            st.write(f'**Type:** {doc.doc_type} · **Classification score:** {doc.classification_confidence:.0%} · **Pages:** {doc.page_count} · **SHA-256:** `{doc.sha256}`')
            a,b=st.columns(2)
            with a:
                st.subheader('Extracted fields'); st.json(doc.fields or {'status':'No fields matched extraction patterns'})
                st.subheader('Original extracted text'); st.text_area('OCR output',doc.text,height=350,disabled=True)
            with b:
                st.subheader('Original page')
                try: st.image(pages_from_bytes(Path(doc.path).read_bytes(),doc.name)[0][1],use_container_width=True)
                except Exception as e: st.error(f'Preview unavailable: {e}')
    elif page=='Visual Forensics':
        st.header('Visual forensics'); st.caption('Heuristic visual observations are not proof of editing or fraud. Results depend on format and image history.')
        if not docs: st.info('Select an investigation with documents to view analysis.')
        else:
            choices=[d for d in docs]; doc=st.selectbox('Source document',choices,format_func=lambda d:d.name); pages=pages_from_bytes(Path(doc.path).read_bytes(),doc.name)
            page_num=st.selectbox('Page',[p[0] for p in pages]); _,image,_=pages[page_num-1]
            if image.info.get('docutrace_placeholder'):
                st.warning('The original PDF page could not be rasterized because its native renderer is blocked. Showing a text-only fallback preview; visual forensics is unavailable for this page.')
                st.text_area('Extracted page text',pages[page_num-1][2],height=180,disabled=True)
                heat,regions=image,[]
            elif Path(doc.name).suffix.lower() in ('.jpg','.jpeg'):
                heat,regions=ela(image,ELA_QUALITY); st.caption(f'ELA quality {ELA_QUALITY}; recompression may produce variation on authentic images.')
            else: heat,regions=visual_difference(image); st.caption('ELA is intended for JPEG; showing a local contrast/noise residual map for this format.')
            x,y=st.columns(2); x.image(image,caption='Original evidence',use_container_width=True); y.image(heat,caption='Heuristic heatmap',use_container_width=True)
            st.write('Candidate regions (page pixel coordinates)'); st.json(regions) if regions else st.caption('No candidate regions met the configured heuristic threshold.')
    elif page=='Contextual Intelligence':
        st.header('Contextual intelligence'); st.caption('Deterministic field comparisons, based only on extracted values. Missing fields are not inferred.')
        if not active: st.info('Select an investigation first.')
        else:
            for doc in docs:
                st.markdown(f"**{doc.name}** · {doc.doc_type} · Extracted fields: {', '.join(doc.fields.keys()) or 'None'}")
            if findings:
                for f in findings: st.markdown(f'**{f.category} · {f.severity}** — {f.description}')
            else: st.success('No discrepancy was detected among the fields successfully extracted. This is not a guarantee that documents are authentic or complete.')
    elif page=='Findings & Evidence':
        st.header('Findings & evidence')
        if not active: st.info('Select an investigation first.')
        elif not findings: st.success('No findings yet. Findings are generated only from observed differences.')
        else:
            for f in findings:
                st.markdown(f'<div class="finding"><b>{f.severity} · {f.category}</b><br><b>{f.title}</b><br>{f.description}</div>',unsafe_allow_html=True)
                refs=f.evidence.get('documents',[]); st.caption('Source documents: '+', '.join(next((d.name for d in docs if d.id==ref),ref[:8]) for ref in refs))
                with st.form(f'review{f.id}'):
                    state=st.selectbox('Review status',['Needs review','Reviewed','Resolved','Dismissed'],index=['Needs review','Reviewed','Resolved','Dismissed'].index(f.status if f.status in ['Needs review','Reviewed','Resolved','Dismissed'] else 'Needs review'),key=f'state{f.id}')
                    note=st.text_input('Reviewer note',value=f.reviewer_note,key=f'note{f.id}')
                    if st.form_submit_button('Save review'):
                        f.status=state; f.reviewer_note=note; db.commit(); audit(db,active.id,'Finding review updated',f'{f.title}: {state}'); st.rerun()
    elif page=='Investigation Reports':
        st.header('Investigation reports')
        if not active: st.info('Select an investigation first.')
        else:
            st.write(f'**{active.title}** · {len(docs)} documents · {len(findings)} findings')
            if st.button('Generate dossier PDF',type='primary'):
                try:
                    from reports.dossier_generator import make_report
                    blob=make_report(active,docs,findings); report_path=DATA/'reports'/f'{active.id}.pdf'; report_path.write_bytes(blob); audit(db,active.id,'Report generated',report_path.name)
                    st.download_button('Download dossier',blob,file_name=f'DocuTrace-{active.id[:8]}.pdf',mime='application/pdf')
                except Exception as e: st.error(f'Report generation failed: {e}')
    elif page=='Settings':
        import shutil, os
        st.header('Settings and capability status')
        st.write(f'Maximum upload per file: **{MAX_UPLOAD_MB} MB**'); st.write(f'ELA JPEG recompression quality: **{ELA_QUALITY}**')
        st.write(f'Tesseract executable: **{shutil.which("tesseract") or os.getenv("TESSERACT_CMD") or "not found"}**')
        st.write(f'LLM API key configured: **{"Yes" if os.getenv("OPENAI_API_KEY") else "No"}** (unused; optional assistant not enabled)')
        st.caption('Uploaded content is kept locally in data/uploads. SQLite audit events are not tamper-proof. Configure values in .env and restart.')
    else:
        st.header('About DocuTrace AI')
        st.write('DocuTrace AI is a local-first document review prototype combining PDF text extraction, optional Tesseract OCR, pattern-based structured fields, OpenCV/Pillow visual heuristics, deterministic cross-document comparison, SQLite persistence and PDF reporting.')
        st.warning('This prototype does not establish authenticity, identify fraud, reliably read handwritten text, or provide certified forensic analysis. OCR and field patterns may miss or misread information. Human review is required.')
        st.markdown('[Architecture documentation](docs/architecture.md) · [Limitations](docs/limitations.md) · [Demo scenarios](docs/demo_scenarios.md)')
