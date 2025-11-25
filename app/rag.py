import os
import uuid
from typing import List, Dict
from pypdf import PdfReaderr
import chromadb
from chromadb.config import Settings
import ollama

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectorstore")
os.makedirs(CHROMA_DIR, exist_ok=True)

# Create the chroma client
client = chromadb.Client(
    Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR)
)

# Creates or gets the collection
collection  = client.get_or_create_collection(
    name="pdf_chunks"
)