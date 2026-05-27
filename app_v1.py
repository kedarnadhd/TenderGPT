# import streamlit as st
# import fitz
# import os
# import pandas as pd
# import uuid
# import unicodedata
# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.llms import Ollama

# # --------------------------------
# # CONFIG
# # --------------------------------
# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# FIELD_MAP = {
#     "Purchase / Service Requisition numbers": [
#         "buyer added bid specific terms",
#         "consignee requirement",
#         "purchase requisition",
#         "service requisition"
#     ],
#     "Tender Number": [
#         "bid number",
#         "gem bid no",
#         "bid no"
#     ],
#     "Tender subject": [
#         "item category",
#         "item title",
#         "schedule of requirement"
#     ],
#     "Tender publishing date": [
#         "dated",
#         "creation date"
#     ],
#     "Bid due date": [
#         "bid end date",
#         "bid end date/time"
#     ],
#     "Bid opening date": [
#         "bid opening date",
#         "technical opening"
#     ],
#     "Bid validity date": [
#         "bid offer validity",
#         "offer validity"
#     ],
#     "Earnest Money deposit (INR)": [
#         "emd amount",
#         "earnest money"
#     ],
#     "Average annual turnover (INR)": [
#         "average annual turnover",
#         "oem average turnover"
#     ],
#     "Working capital (INR)": [
#         "working capital",
#         "liquid assets"
#     ],
#     "Make in India policy": [
#         "mii purchase preference",
#         "make in india"
#     ],
#     "Evaluation Methodology (Award)": [
#         "evaluation methodology",
#         "l1"
#     ]
# }

# # --------------------------------
# # MODEL LOADING
# # --------------------------------
# @st.cache_resource
# def load_models():
#     embedding = HuggingFaceEmbeddings(
#         model_name="sentence-transformers/all-MiniLM-L6-v2"
#     )
#     llm = Ollama(model="llama3.1")
#     return embedding, llm

# embedding, llm = load_models()

# # --------------------------------
# # PDF PARSER
# # --------------------------------
# def extract_pdf_pages(pdf_path):
#     doc = fitz.open(pdf_path)
#     pages = []

#     for page_num, page in enumerate(doc):
#         text = page.get_text()
#         pages.append({
#             "page": page_num + 1,
#             "text": text
#         })

#     return pages

# # --------------------------------
# # CHUNKER
# # --------------------------------
# def create_chunks(pages, chunk_size=1800):
#     chunks = []
#     metadata = []

#     for page in pages:
#         text = page["text"]

#         for i in range(0, len(text), chunk_size):
#             chunk = text[i:i+chunk_size]

#             if chunk.strip():
#                 chunks.append(chunk)
#                 metadata.append({"page": page["page"]})

#     return chunks, metadata

# # --------------------------------
# # VECTOR DB
# # --------------------------------
# def build_vector_db(chunks, metadata):
#     db = Chroma.from_texts(
#         texts=chunks,
#         embedding=embedding,
#         metadatas=metadata,
#         collection_name=f"temp_{uuid.uuid4().hex[:8]}"
#     )
#     return db

# # --------------------------------
# # LABEL TO VALUE EXTRACTION
# # --------------------------------
# def extract_value_after_label(full_text, aliases):
#     lines = [line.strip() for line in full_text.split("\n") if line.strip()]

#     for idx, line in enumerate(lines):
#         line_lower = line.lower()

#         for alias in aliases:
#             if alias.lower() in line_lower:
#                 candidates = []

#                 # Same line value after colon
#                 if ":" in line:
#                     part = line.split(":", 1)[-1].strip()
#                     if len(part) > 3:
#                         candidates.append(part)

#                 # next 3 lines
#                 for j in range(1, 4):
#                     if idx + j < len(lines):
#                         next_line = lines[idx + j].strip()
#                         if len(next_line) > 3:
#                             candidates.append(next_line)

#                 for c in candidates:
#                     if not any(a.lower() in c.lower() for a in aliases):
#                         return c

#     return None

# # --------------------------------
# # FIELD EXTRACTION
# # --------------------------------
# def extract_fields(db, full_text):
#     results = {}

#     for field, aliases in FIELD_MAP.items():

#         # 1. Direct nearby extraction
#         value = extract_value_after_label(full_text, aliases)

#         if value:
#             results[field] = value
#             continue

#         # 2. Semantic fallback
#         collected = []

#         for alias in aliases:
#             docs = db.similarity_search(alias, k=3)

#             for doc in docs:
#                 collected.append(doc.page_content)

#         context = "\n".join(list(set(collected)))[:6000]

#         prompt = f"""
# You are an expert tender analyst.

# Extract exact value for:
# {field}

# Equivalent terms:
# {', '.join(aliases)}

# Return only value.
# If unavailable return Not Found.

# Text:
# {context}
# """

#         try:
#             answer = llm.invoke(prompt).strip()
#         except:
#             answer = "Not Found"

#         results[field] = answer

#     return results

# # --------------------------------
# # APP UI
# # --------------------------------
# st.set_page_config(page_title="TenderGPT V2.1", layout="wide")
# st.title("📄 TenderGPT V2.1 — GeM Tender Extractor")

# uploaded_file = st.file_uploader("Upload Tender PDF", type=["pdf"])

# if uploaded_file:
#     save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

#     with open(save_path, "wb") as f:
#         f.write(uploaded_file.read())

#     st.success("PDF uploaded")

#     with st.spinner("Reading PDF..."):
#         pages = extract_pdf_pages(save_path)

#     st.write(f"Total pages: {len(pages)}")

#     # First 15 pages usually enough for metadata
#     pages = pages[:15]

#     full_text = "\n".join([p["text"] for p in pages])

#     # Normalize
#     full_text = unicodedata.normalize("NFKD", full_text)
#     full_text = full_text.encode("ascii", "ignore").decode("utf-8")

#     with st.spinner("Creating chunks..."):
#         chunks, metadata = create_chunks(pages)

#     with st.spinner("Building semantic index..."):
#         db = build_vector_db(chunks, metadata)

#     if st.button("Extract Tender Details"):
#         with st.spinner("Extracting..."):
#             results = extract_fields(db, full_text)

#         st.subheader("Extracted Tender Details")
#         st.json(results)

#         df = pd.DataFrame([results])
#         csv = df.to_csv(index=False)

#         st.download_button(
#             "Download CSV",
#             csv,
#             file_name="tender_output.csv",
#             mime="text/csv"
#         )

#     # --------------------------------
#     # Semantic Search
#     # --------------------------------
#     st.subheader("🔍 Semantic Search")

#     query = st.text_input("Search any term inside tender")

#     if query:
#         docs = db.similarity_search(query, k=5)

#         for i, doc in enumerate(docs):
#             st.markdown(f"### Result {i+1}")
#             st.markdown(f"**Page:** {doc.metadata.get('page')}")
#             st.write(doc.page_content[:1200])
#             st.markdown("---")

#     # --------------------------------
#     # Debug Raw Text
#     # --------------------------------
#     with st.expander("View extracted raw text (debug)"):
#         st.text(full_text[:8000])