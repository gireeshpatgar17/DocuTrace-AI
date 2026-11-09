# Implementation status and limitations

## Implemented

- PDF/image signature checks, upload size caps, SHA-256, local original storage.
- PDF text extraction and page rendering; optional Tesseract English OCR with word boxes and confidence.
- Keyword document classification, regex field extraction, and deterministic cross-document checks for name, address, salary, and birth date.
- OpenCV residual visualization and JPEG recompression ELA with candidate regions.
- SQLite investigations, documents, findings, and audit events; reviewer status and notes.
- Generated PDF dossier and local dashboard statistics.

## Partial

- Extraction patterns cover a narrow set of English labels and may not support varied layouts.
- OCR confidence is page-level and only attached in the processing result; not all field values have reliable source boxes.
- Visual methods are heuristic: candidate regions can arise from normal compression, texture, or scanning.
- Report includes summaries and hashes but does not embed every source page or region image.
- If Windows Application Control blocks PyMuPDF's native renderer, digital PDF text still extracts through pypdf, but page previews become text-only and image forensics cannot run on those PDF pages.
- Audit events are ordinary local SQLite records, not immutable.

## Not implemented

- LLM assistant, table/layout understanding, handwritten OCR, signatures, robust identity/entity graph, document field correction UI, reviewer audit for per-field corrections, PDF evidence highlight viewer, multilingual processing, advanced deduplication, formal forensic validation, tamper-proof audit, cloud sync, and export of a structured evidence package.
- Synthetic scenarios beyond the generated starter documents described in demo docs.

This tool cannot determine document authenticity or whether a person committed fraud. Findings are review cues, not conclusions. Do not treat missing findings as verification.
