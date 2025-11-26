import os
import json
import uuid
from typing import List, Dict
from pypdf import PdfReader
import numpy as np
import faiss
import ollama

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INDEX_PATH = os.path.join(DATA_DIR, "index.faiss")
CHUNKS_PATH = os.path.join(DATA_DIR, "chunks.json")

os.makedirs(DATA_DIR, exist_ok=True)

# -----------------------------
# PDF TEXT EXTRACTION
# -----------------------------
def extract_text_from_file(path: str) -> Dict:
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            texts.append(page_text)
        full_text = "\n".join(texts)
        return {"text": full_text, "meta": {"pages": len(texts)}}
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")

# -----------------------------
# CHUNKING
# -----------------------------
def chunk_text(text: str, chunk_size: int = 400, overlap: float = 0.2) -> List[str]:
    words = text.split()
    if not words:
        return []
    
    step = int(chunk_size * (1 - overlap)) or 1
    chunks = []
    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
    return chunks

# -----------------------------
# FAISS HELPER
# -----------------------------
def _make_faiss_index(embedding_dim: int):
    return faiss.IndexFlatIP(embedding_dim)

def _normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return v / norm

# -----------------------------
# STORAGE
# -----------------------------
def _load_chunks() -> Dict[str, Dict]:
    if not os.path.exists(CHUNKS_PATH):
        return {}
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_chunks(data: Dict[str, Dict]):
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -----------------------------
# EMBEDDINGS (Fixed)
# -----------------------------
def embed_texts(texts: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
    if not texts:
        return []
    
    results = []
    # Ollama embeddings endpoint works on single strings. We must loop.
    for text in texts:
        resp = ollama.embeddings(model=model, prompt=text)
        if "embedding" in resp:
            results.append(resp["embedding"])
        else:
            # Fallback for empty/error
            results.append([0.0] * 768) 
            
    return results

# -----------------------------
# INDEX MANAGEMENT
# -----------------------------
def _ensure_index_loaded():
    chunks = _load_chunks()
    if os.path.exists(INDEX_PATH) and chunks:
        index = faiss.read_index(INDEX_PATH)
        return index, chunks
    return None, chunks

def _write_index(index):
    faiss.write_index(index, INDEX_PATH)

def clear_index():
    """Utility to clear data for testing"""
    if os.path.exists(INDEX_PATH): os.remove(INDEX_PATH)
    if os.path.exists(CHUNKS_PATH): os.remove(CHUNKS_PATH)

# -----------------------------
# INGEST
# -----------------------------
def ingest_pdf_text(text: str, model: str = "nomic-embed-text") -> List[str]:
    chunks = chunk_text(text)
    if not chunks:
        return []

    embeddings = embed_texts(chunks, model=model)
    embeddings_np = np.array(embeddings).astype("float32")
    embeddings_np = _normalize(embeddings_np)

    index, chunks_meta = _ensure_index_loaded()
    
    # Initialize index if strictly necessary
    if index is None:
        dim = embeddings_np.shape[1]
        index = _make_faiss_index(dim)
        # If we had metadata but no index file, we should technically re-embed everything.
        # For this simple app, we assume they stay in sync or we clear_index() on start.

    # Add IDs
    new_ids = []
    for chunk in chunks:
        cid = str(uuid.uuid4())
        new_ids.append(cid)
        chunks_meta[cid] = {"text": chunk}

    index.add(embeddings_np)
    _write_index(index)
    _save_chunks(chunks_meta)
    return new_ids

# -----------------------------
# SEARCH
# -----------------------------
def search(query: str, top_k: int = 4, model: str = "nomic-embed-text") -> List[Dict]:
    index, chunks_meta = _ensure_index_loaded()
    if index is None or not chunks_meta:
        return []

    q_emb = np.array(embed_texts([query], model=model)).astype("float32")
    q_emb = _normalize(q_emb)

    D, I = index.search(q_emb, top_k)
    
    # Map index positions back to chunk IDs using keys order
    # NOTE: This assumes keys() order is stable (Python 3.7+) and matches insertion order
    ids_list = list(chunks_meta.keys())
    
    results = []
    # I[0] is the list of indices for the first query
    for pos, score in zip(I[0], D[0]):
        if pos < 0 or pos >= len(ids_list):
            continue
        cid = ids_list[pos]
        results.append({
            "id": cid, 
            "text": chunks_meta[cid]["text"], 
            "score": float(score)
        })
    return results