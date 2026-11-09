from core.analysis import validate_file, classify, extract_fields, normalize, compare_documents
import pytest

def test_validates_signatures_and_rejects_mismatch():
    assert validate_file('a.pdf',b'%PDF-1.4')=='application/pdf'
    with pytest.raises(ValueError): validate_file('a.png',b'%PDF-1.4')
    with pytest.raises(ValueError): validate_file('bad.exe',b'abc')

def test_classify_and_extract_real_text():
    text='APPLICATION FORM\nApplicant: Maya Rao\nDeclared income: INR 75,000\nDate of birth: 02/04/1990'
    assert classify(text)[0]=='Application Form'
    result=extract_fields(text)
    assert result['name']=='Maya Rao' and result['date_of_birth']=='02/04/1990'

def test_normalized_cross_document_discrepancy():
    assert normalize('Maya-Rao')==normalize('Maya Rao')
    docs=[{'id':'a','name':'form','fields':{'name':'Maya Rao','salary':'75,000'}},{'id':'b','name':'slip','fields':{'name':'Maya Rao','salary':'92,000'}}]
    findings=compare_documents(docs)
    assert len(findings)==1 and findings[0]['category']=='Financial discrepancy'

def test_no_finding_for_normalized_match():
    assert compare_documents([{'id':'a','name':'a','fields':{'name':'Maya Rao'}},{'id':'b','name':'b','fields':{'name':'maya-rao'}}])==[]

def test_salary_labels_are_compared_without_treating_bank_credit_as_gross_salary():
    from core.analysis import extract_fields
    assert extract_fields('Declared income: INR 75,000')['salary']=='75,000'
    assert 'salary' not in extract_fields('Salary credit: INR 68,500')

def test_collapses_many_name_differences_into_one_evidence_finding():
    docs=[{'id':str(i),'name':name,'fields':{'name':value}} for i,(name,value) in enumerate([('form','Maya Rao'),('id','Maya Rao'),('address','M. Rao'),('bank','Rohan Shah')])]
    found=[f for f in compare_documents(docs) if f['category']=='Identity discrepancy']
    assert len(found)==1
    assert len(found[0]['documents'])==4
