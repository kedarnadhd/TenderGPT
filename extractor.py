from langchain_community.llms import Ollama
from config import FIELDS
from reliability.confidence import calculate_confidence

llm = Ollama(model="llama3.1")

def extract_fields(db):
    results = {}

    for main_field, synonyms in FIELDS.items():
        collected_chunks = []

        # for term in synonyms:
        #     docs = db.similarity_search(term, k=2)

        #     for d in docs:
        #         collected_chunks.append(d.page_content)

        source_page = None
        extraction_method = "semantic"

        for term in synonyms:
            
            docs = db.similarity_search(term, k=2)

            if docs and source_page is None:
                source_page = docs[0].metadata.get("page")

            for d in docs:
                collected_chunks.append(d.page_content)

        context = "\n".join(list(set(collected_chunks)))[:12000]

        prompt = f"""
You are an expert Indian tender analyst.

Find exact value for:

{main_field}

Use semantic understanding.
Related meanings:
{', '.join(synonyms)}

Rules:
1. Return concise answer only.
2. If unavailable return Not Found.
3. Extract exact INR values where possible.
4. Understand synonymous phrases.
5. Do not explain.

Document text:
{context}
"""

        answer = llm.invoke(prompt)

        confidence  = calculate_confidence(extraction_method, answer)

        results[main_field] = {
            "value": answer,
            "page": source_page,
            "confidence": confidence,
            "method": extraction_method
}

    return results