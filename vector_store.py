# from langchain_community.vectorstores.chroma import Chroma
from langchain_community.vectorstores.faiss import FAISS

from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.embeddings.ollama import OllamaEmbeddings


embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# embedding = OllamaEmbeddings(
#     model= "nomic-embed-text"
# )

# VECTOR_DB_DIR = "vector_db"


def build_vector_db(chunks , metadata):
    db = FAISS.from_texts(
        texts=chunks,
        embedding=embedding,
        metadatas=metadata,
    )
    return db