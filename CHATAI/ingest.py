import os
import logging
from dotenv import load_dotenv

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
)
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings
import qdrant_client

# Setup logging to see the progress
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
QDRANT_PATH = "./qdrant_data"  # Directory where Qdrant will store its data
QDRANT_COLLECTION_NAME = "previous_year_questions"
DATA_DIR = "data"  # Directory containing your PDF question papers

def extract_metadata(file_path: str) -> dict:
    """
    Extracts metadata from the filename.
    Example filename: '30-2-2_Mathematics Standard.pdf'
    """
    try:
        # Get just the filename, without the directory path or .pdf extension
        filename = os.path.basename(file_path).replace('.pdf', '')
        
        # Split the filename into the code part and the subject part at the first underscore
        code_part, subject_part = filename.split("_", 1)
        
        # Split the code part into its components
        code_numbers = code_part.split("-")
        
        metadata = {
            "code": code_part,             # full code like "30-2-2"
            "code_parts": code_numbers,    # list like ["30", "2", "2"]
            "subject": subject_part.strip() # subject like "Mathematics Standard"
        }
        return metadata
    
    except Exception as e:
        logging.warning(f"Could not parse metadata from filename: {file_path}. Error: {e}")
        return {}

def ingest_data():
    """
    Reads PDFs from the DATA_DIR, creates a hierarchical node structure,
    and stores them in the Qdrant vector store and local storage.
    """
    logging.info("Starting data ingestion process...")
    
    # Configure LlamaIndex global settings for the LLM and embedding model
    Settings.llm = OpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY"))

    try:
        # Initialize the Qdrant client for local on-disk storage
        client = qdrant_client.QdrantClient(path=QDRANT_PATH)
        
        # Create the LlamaIndex vector store wrapper
        vector_store = QdrantVectorStore(client=client, collection_name=QDRANT_COLLECTION_NAME)

        # Load all documents from the data directory, applying metadata extraction
        documents = SimpleDirectoryReader(DATA_DIR, file_metadata=extract_metadata).load_data()
        if not documents:
            logging.warning(f"No documents found in '{DATA_DIR}'. Aborting.")
            return

        # Create a hierarchical node parser to split documents into a parent/child structure
        node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[2048, 512, 128])
        nodes = node_parser.get_nodes_from_documents(documents)
        leaf_nodes = get_leaf_nodes(nodes)

        # Create a storage context, linking our vector store
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Add ALL nodes (parents and children) to the document store.
        # This is crucial for the auto-merging retriever to find parent context.
        storage_context.docstore.add_documents(nodes)
        
        # Build the vector index using only the smallest (leaf) nodes for embedding.
        # This is efficient and provides specific results.
        index = VectorStoreIndex(
            leaf_nodes,
            storage_context=storage_context,
            show_progress=True
        )
        
        # Persist the LlamaIndex-specific parts (like the docstore) to a local directory
        storage_context.persist(persist_dir="./storage")

        logging.info(f"Successfully created and persisted index to Qdrant ('./qdrant_data') and local storage ('./storage').")

    except Exception as e:
        logging.error(f"An error occurred during data ingestion: {e}", exc_info=True)

if __name__ == "__main__":
    ingest_data()