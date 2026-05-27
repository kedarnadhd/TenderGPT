Project idea: TenderGPT Lite — Extract structured fields from 100-page tender PDFs

Goal: Upload a long tender PDF (100+ pages), automatically extract key procurement fields into a structured table/JSON.

What it extracts

From each uploaded tender document:

Purchase / Service Requisition numbers
Tender Number
Tender subject
Tender publishing date
Bid due date
Bid opening date
Bid validity date
Earnest Money Deposit (EMD) (INR)
Average annual turnover (INR)
Working capital (INR)
Make in India policy
Evaluation Methodology (Award)



Some hints of Tech stack

Use this because you’re on Windows and already use Streamlit/Docker:

Streamlit → UI
PyMuPDF → PDF text extraction
spaCy → regex + NLP extraction
Ollama → local LLM
Chroma → optional semantic retrieval
Pandas → export results