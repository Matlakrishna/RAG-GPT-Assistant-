import faiss
import numpy as np
import pdfplumber
import docx
from sentence_transformers import SentenceTransformer

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # Small, efficient model

# Store document data (in-memory for now)
document_store = {}

# FAISS index for similarity search
dimension = 384  # Matching the embedding model output
index = faiss.IndexFlatL2(dimension)

# Extract text from different file types
def extract_text_from_file(file_path):
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        return extract_text_from_word(file_path)
    elif file_path.endswith(".txt"):
        return extract_text_from_txt(file_path)
    else:
        return "Unsupported file type"

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_text_from_word(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

# Add document to FAISS and store text
def add_document(file_path):
    text = extract_text_from_file(file_path)
    if text.strip():
        doc_id = len(document_store)  # Assign unique ID
        document_store[doc_id] = text
        
        # Convert text to embeddings
        text_embedding = embedding_model.encode([text])[0]  # Get vector representation
        text_embedding = np.array([text_embedding]).astype("float32")

        # Add to FAISS index
        index.add(text_embedding)
        
        return f"✅ File '{file_path}' added to knowledge base."
    return "❌ Could not extract text."

# Perform a search query
def search_documents(query, top_k=3):
    query_embedding = embedding_model.encode([query])[0]
    query_embedding = np.array([query_embedding]).astype("float32")

    if index.ntotal == 0:
        return "No documents found. Please upload a file first."

    # Search in FAISS
    distances, indices = index.search(query_embedding, top_k)

    results = []
    for idx in indices[0]:
        if idx in document_store:
            results.append(document_store[idx])

    return results if results else ["No relevant documents found."]
