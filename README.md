# DocuTrace AI

**Beyond OCR. Towards Intelligent Document Investigation.**

DocuTrace AI is a local-first Streamlit prototype for processing related documents, extracting text and selected fields, comparing values across documents, reviewing visual heuristics, and producing an evidence-linked PDF dossier. It is a decision-support tool; it does not determine authenticity or fraud.

## Live demo

Try the deployed application at [docutrace-ai.streamlit.app](https://docutrace-ai.streamlit.app). Use only the included fictional demonstration documents; this prototype is not intended for sensitive records.

## Capabilities

- Create separate investigations; upload multiple PDF, PNG, or JPEG documents.
- Verify extension against file signature and enforce a per-file size limit; preserve originals and record SHA-256.
- Extract digital PDF text with PyMuPDF, or fall back to pure-Python pypdf extraction if a Windows policy blocks the native PDF renderer; use Tesseract OCR for image/scanned content when installed.
- Predict document category from extracted content; extract a limited set of labeled fields with regex.
- Compare extracted names, addresses, salaries, and dates across documents using normalized deterministic rules.
- Show original pages, JPEG ELA or a local residual heatmap with candidate regions.
- Persist investigations, findings, reviewer notes/status and audit events in SQLite.
- Generate and download a ReportLab dossier.

## Architecture and implementation status

See [architecture](docs/architecture.md), [limitations](docs/limitations.md), and [demo scenarios](docs/demo_scenarios.md). The application implements the core prototype flow. LLM explanations, table understanding, field-level edits, evidence-region viewer, robust entity graph, immutable audit, broad document schemas, and multilingual/handwriting OCR are not implemented. The dashboard and analysis are generated from stored processing records, not fabricated metrics.

## Requirements and setup (Windows)

Python 3.12 or 3.14 is suitable with the pinned packages below. From this folder:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Install [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) to enable OCR on scanned documents and images; English language data should be selected. Add the executable to PATH or set `TESSERACT_CMD` in `.env`. Digital PDFs with embedded text work without Tesseract. OCR calls the Tesseract command-line executable directly; PDF handling uses PyMuPDF with a pypdf fallback; images use Pillow/OpenCV; persistence uses SQLAlchemy/SQLite; reports use ReportLab; charts use Plotly.

## Run

```powershell
streamlit run app.py
```

Data is stored locally in `data/docutrace.sqlite3`, originals in `data/uploads`, and generated reports in `data/reports`. Back up these folders as needed. Do not upload documents unless authorized.

## Demonstration data

Generate fictional examples with:

```powershell
python scripts/create_demo_data.py
```

Upload the five files from `data/demo/clean` into one investigation and inspect extracted fields and the no-discrepancy outcome. Then process `data/demo/contextual_discrepancy` separately to see field differences where extraction patterns detect them. Compare original and modified PNGs in `data/demo/visual_manipulation` under Visual Forensics. Scenario expectations are in `docs/demo_scenarios.md`; they are not injected into findings.

## Tests

```powershell
pytest -q
```

Tests cover signature validation, extraction, classification, normalization and deterministic comparison. They do not claim complete system or forensic validation.

## Safety, privacy, and limitations

Uploaded files and extracted text stay local by default; the optional API key placeholder is unused. Restrict filesystem access and protect local backups. OCR can be wrong, extraction can miss fields, and normal compression can trigger visual heuristics. A finding is a cue to investigate, not proof. A clean result is not proof of authenticity. The audit database is not tamper-proof, and the application does not claim standards compliance or certification.

## Future work

Field-specific schemas and source boxes, human correction with audit history, evidence crop viewer, table/layout understanding, configurable comparisons, stronger scenario integration tests, tamper-evident logs, and optional user-configured LLM summaries grounded in evidence.
