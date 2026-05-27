import streamlit as st
import fitz
import shutil
import os
import pandas as pd
import uuid
import unicodedata
import re
import time

# from langchain_community.vectorstores.chroma import Chroma
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
# from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from reliability.smart_chunker import create_smart_chunks
from reliability.confidence import calculate_confidence
from reliability.search_utils import smart_search

# --------------------------------
# CONFIG
# --------------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

FIELD_MAP = {
    "Purchase / Service Requisition numbers": [
        "buyer added bid specific terms",
        "consignee requirement",
        "purchase requisition",
        "service requisition"
    ],
    "Tender Number": [
        "bid number",
        "gem bid no",
        "bid no",
        "tender number"
    ],
    "Tender subject": [
        "item category",
        "item title",
        "schedule of requirement"
    ],
    "Tender publishing date": [
        "dated",
        "creation date",
        "date of rfp issue",
        "rfp issue date",
        "published date"
    ],
    "Bid due date": [
        "bid end date",
        "bid end date/time",
        "last date of submission"
    ],
    "Bid opening date": [
        "bid opening date",
        "technical opening",
        "opening date"
    ],
    "Bid validity date": [
        "bid offer validity",
        "offer validity"
    ],
    "Earnest Money deposit (INR)": [
        "emd amount",
        "earnest money",
        "bid security",
        "bid security (earnest money deposit-emd)"
    ],
    "Average annual turnover (INR)": [
        "average annual turnover",
        "oem average turnover"
    ],
    "Working capital (INR)": [
        "working capital",
        "liquid assets"
    ],
    "Make in India policy": [
        "mii purchase preference",
        "make in india"
    ],
    "Evaluation Methodology (Award)": [
        "evaluation methodology",
        "l1"
    ]
}

# --------------------------------
# MODEL LOADING
# --------------------------------
@st.cache_resource
def load_models():
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # embedding = OllamaEmbeddings(
    #     model= "nomic-embed-text"
    # )
    llm = Ollama(model="llama3.1")
    return embedding, llm

embedding, llm = load_models()

# --------------------------------
# PDF PARSER
# --------------------------------
def extract_pdf_pages(pdf_path):

    start = time.time()

    doc = fitz.open(pdf_path)

    pages = []

    for page_num in range(len(doc)):

        page = doc.load_page(page_num)

        text = page.get_text()

        pages.append({
            "page": page_num + 1,
            "text": text
        })

    end = time.time()

    st.write(f"PDF Reading Time: {round(end-start,2)} sec")

    return pages

# --------------------------------
# CHUNKER
# --------------------------------
def create_chunks(pages):

    start = time.time()

    chunks, metadata = create_smart_chunks(pages)

    end = time.time()

    st.write(f"Chunk Creation Time: {round(end - start, 2)} sec")

    return chunks, metadata

# --------------------------------
# VECTOR DB
# --------------------------------
def build_vector_db(chunks, metadata):
    db = FAISS.from_texts(
        texts=chunks,
        embedding=embedding,
        metadatas=metadata,
        persist_directory="chroma_store",
        collection_name=f"temp_{uuid.uuid4().hex[:8]}"
    )
    return db

# --------------------------------
# CLEAN VALUE
# --------------------------------
def clean_value(value, aliases):
    if not value:
        return None

    value = value.strip()
    value = re.sub(r"\s+", " ", value)

    if len(value) < 3:
        return None

    for alias in aliases:
        if alias.lower() == value.lower():
            return None

    return value

# --------------------------------
# SPECIAL DATE EXTRACTION
# --------------------------------
def extract_publish_date_from_bid_block(full_text):
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    months = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]

    for i, line in enumerate(lines):
        if "bid number" in line.lower():
            for j in range(1, 4):
                if i + j < len(lines):
                    next_line = lines[i + j]

                    if any(month in next_line.lower() for month in months):
                        return next_line

    return None

# --------------------------------
# NEIGHBOR EXTRACTION
# --------------------------------
def extract_value_after_label(full_text, aliases):
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    for idx, line in enumerate(lines):
        line_lower = line.lower()

        for alias in aliases:
            if alias.lower() in line_lower:
                candidates = []

                if ":" in line:
                    part = line.split(":", 1)[-1].strip()
                    if part:
                        candidates.append(part)

                for j in range(1, 4):
                    if idx + j < len(lines):
                        candidates.append(lines[idx + j])

                for candidate in candidates:
                    cleaned = clean_value(candidate, aliases)
                    if cleaned:

                            # reject long noisy paragraphs
                        if len(cleaned) > 120:
                            continue

                            # reject document names
                        reject_words = [
                            "certificate",
                            "document",
                            "pdf",
                            "uploaded"
                        ]

                        if any(word in cleaned.lower() for word in reject_words):
                            continue

                        return cleaned

    return None

# --------------------------------
# FIELD EXTRACTION
# --------------------------------
def extract_fields(db, full_text, chunks, metadata):
    results = {}

    for field, aliases in FIELD_MAP.items():

        # Special case for publishing date
        if field == "Tender publishing date":
            special_date = extract_publish_date_from_bid_block(full_text)
            if special_date:
                results[field] = special_date
                continue

        # direct extraction
        value = extract_value_after_label(full_text, aliases)

        if value:
            results[field] = {
                "value": value,
                "page": "Direct Match",
                "confidence": calculate_confidence("regex", value),
                "method": "regex"
            }

            continue

        # semantic fallback
        collected = []

        source_page = None
        extraction_method = "semantic"

        QUERY_EXPANSION = {
                "emd": "earnest money deposit bid security emd amount",
                "turnover": "average annual turnover financial turnover",
                "bid date": "bid end date bid due date submission date",
            }

        for alias in aliases:

            keyword_docs = []

            for chunk, meta in zip(chunks, metadata):

                if alias.lower() in chunk.lower():
                    keyword_docs.append({
                        "text": chunk,
                        "page": meta["page"]
                    })

            # if exact keyword matches found
            if keyword_docs:

                for item in keyword_docs[:3]:
                    collected.append(item["text"])

                if source_page is None:
                    source_page = keyword_docs[0]["page"]

                continue

            # --------------------------------
            # SEMANTIC FALLBACK
            # --------------------------------

            search_query = QUERY_EXPANSION.get(
                alias.lower(),
                alias
            )

            docs = smart_search(
                db,
                search_query,
                aliases=aliases
            )

            if docs and source_page is None:

                source_page = docs[0].metadata.get(
                    "page",
                    "Unknown"
                )

            for doc in docs:
                collected.append(doc.page_content)
            
        context = "\n".join(
            list(set(collected))
        )[:6000]

        prompt = f"""
You are an expert Indian GeM tender analyst.

Extract exact value for:
{field}

Equivalent terms:
{', '.join(aliases)}

Return only the exact value.
If unavailable return Not Found.

Text:
{context}
"""

        try:
            answer = llm.invoke(prompt).strip()
        except:
            answer = "Not Found"

        confidence = calculate_confidence(
            extraction_method,
            answer
        )

        results[field] = {
            "value": answer,
            "page": source_page,
            "confidence": confidence,
            "method": extraction_method
        }

    return results

# --------------------------------
# APP
# --------------------------------
st.set_page_config(page_title="TenderGPT", layout="wide")
st.title("📄 TenderGPT — Tender Intelligence Extractor")

uploaded_file = st.file_uploader("Upload Tender PDF", type=["pdf"])

if uploaded_file:
    save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

    with open(save_path, "wb") as f:
        f.write(uploaded_file.read())

    st.success("PDF uploaded successfully")

    # -------------------------
    # PDF READING
    # -------------------------
    with st.spinner("Reading PDF..."):

        start = time.time()

        pages = extract_pdf_pages(save_path)

        end = time.time()
    st.write(f"PDF Reading Time: {round(end-start,2)} sec")

    st.write(f"Total pages: {len(pages)}")

    full_text = "\n".join([p["text"] for p in pages])

    full_text = unicodedata.normalize("NFKD", full_text)
    full_text = full_text.encode("ascii", "ignore").decode("utf-8")

    # delete old vector db
    if os.path.exists("vector_db"):
        shutil.rmtree("vector_db")

    # -------------------------
    # CHUNK CREATION
    # -------------------------
        
    with st.spinner("Creating chunks..."):
        start = time.time()

        chunks, metadata = create_smart_chunks(pages)

        end = time.time()

    st.write(f"Chunk Creation Time: {round(end-start,2)} sec")

    st.write(f"Total Chunks: {len(chunks)}")

    if chunks:
        st.write("First Chunk Preview:")
        st.write(chunks[0][:500])        

    # -------------------------
    # VECTOR DB BUILD
    # -------------------------

    with st.spinner("Building semantic search index..."):
        start = time.time()

        db = build_vector_db(chunks, metadata)

        end = time.time()

    st.write(f"Embedding + Index Time: {round(end-start,2)} sec")

    st.success("Semantic index built successfully")

    # -------------------------
    # EXTRACTION
    # -------------------------

    if st.button("Extract Tender Details"):
        with st.spinner("Extracting..."):
            results = extract_fields(db, full_text, chunks, metadata)

        st.subheader("📋 Extracted Tender Details")

        table_rows = []

        for field, data in results.items():

            table_rows.append({
                "Parameter": field,
                "Value": data["value"],
                "Confidence": data["confidence"],
                "Page": data["page"],
                "Method": data["method"]
            })

        table_data = pd.DataFrame(table_rows)

        st.dataframe(table_data, use_container_width=True)

        csv = table_data.to_csv(index=False)

        st.download_button(
            "Download CSV",
            csv,
            file_name="tender_output.csv",
            mime="text/csv"
        )

    st.subheader("🔍 Semantic Search Inside Tender")

    query = st.text_input("Search any clause / keyword")

    if query:
        docs = db.similarity_search(query, k=5)

        for i, doc in enumerate(docs):
            st.markdown(f"### Result {i+1}")
            st.markdown(f"**Page:** {doc.metadata.get('page')}")
            st.write(doc.page_content[:1200])
            st.markdown("---")

    with st.expander("View extracted raw text (debug)"):
        st.text(full_text[:8000])