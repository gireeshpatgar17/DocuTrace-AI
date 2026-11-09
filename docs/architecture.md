# Architecture

```mermaid
flowchart LR
 U[PDF or image upload] --> V[Signature and size validation]
 V --> S[Original evidence store and SHA-256]
 S --> P[PDF text or page rendering]
 P --> O[Tesseract OCR when needed]
 O --> X[Pattern based field extraction]
 X --> C[Document classification]
 C --> R[Deterministic cross-document rules]
 P --> F[OpenCV visual heuristics]
 R --> E[SQLite findings and audit events]
 F --> E
 E --> UI[Streamlit review and evidence UI]
 E --> PDF[ReportLab dossier]
```

`core/analysis.py` contains stateless processing and comparison functions. `models/database.py` defines SQLite persistence. `app.py` orchestrates the workflow and Streamlit views. Original file bytes are saved unchanged; generated previews and report outputs are stored separately. No external LLM is invoked.
