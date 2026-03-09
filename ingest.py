import os
import sys
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- Configuration ---
DB_DIR = "./chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"

def load_document(file_path):
    """Step 1: Extract text from the PDF."""
    print(f"Loading document: {file_path}...")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: Could not find '{file_path}'. Please add a PDF file to the folder.")
        
    loader = PDFPlumberLoader(file_path)
    documents = loader.load()
    
    print(f"Successfully loaded {len(documents)} pages.\n")
    return documents

def chunk_document(documents):
    """Step 2: Break the document into smaller semantic chunks."""
    print("Chunking document into smaller pieces...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,       # Max characters per chunk
        chunk_overlap=150,    # Overlap to prevent cutting clauses in half
        separators=["\n\n", "\n", " ", ""] # Splits by paragraphs first
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Document split into {len(chunks)} chunks.\n")
    return chunks

def create_vector_db(chunks):
    """Step 3 & 4: Convert chunks to vectors and store/append to ChromaDB."""
    print("Loading BGE-M3 embedding model (this may take a minute on first run)...")
    
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    print("Adding documents to Vector Database...")

    # Connect to existing DB or create a new one
    db = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings
    )

    # Add new chunks (appends, does not overwrite existing data)
    db.add_documents(chunks)
    
    print(f"Database successfully updated in '{DB_DIR}' folder!")
    return db

def list_ingested_documents():
    """List all documents currently stored in the database."""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    if not os.path.exists(DB_DIR):
        print("No database found. Run ingestion first.")
        return []

    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    collection = db.get()
    
    # Extract unique source filenames from metadata
    sources = set()
    for meta in collection.get("metadatas", []):
        if meta and "source" in meta:
            sources.add(meta["source"])
    
    return sorted(sources)

if __name__ == "__main__":
    # Accept PDF path as a command-line argument or use default
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = input("Enter the path to the PDF file: ").strip()

    if not pdf_path:
        print("Error: No PDF path provided.")
        sys.exit(1)

    print("=== STARTING INGESTION PROCESS ===")
    
    # 1. Load PDF
    docs = load_document(pdf_path)
    
    # 2. Chunk Text
    chunks = chunk_document(docs)
    
    # 3. Embed & Store (appends to existing DB)
    create_vector_db(chunks)
    
    # 4. Show all ingested documents
    print("\n Documents currently in the database:")
    for doc_name in list_ingested_documents():
        print(f"   • {doc_name}")
    
    print("\n=== INGESTION COMPLETE ===")