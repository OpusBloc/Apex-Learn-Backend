# backend/services.py
import os
import tempfile
import logging
from typing import List
import functools

# --- LlamaIndex / Qdrant Imports ---
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters, FilterCondition
from llama_index.llms.openai import OpenAI
from llama_index.core.agent import AgentRunner
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext, SimpleDirectoryReader
import qdrant_client
from _prompts import get_system_prompt

# --- Configuration ---
# It's best practice to define constants for paths and collection names
QDRANT_PATH = "./qdrant_college_data"
DOC_CHAT_COLLECTION = "user_document_collection"
logger = logging.getLogger(__name__)

# --- Qdrant Client Initialization ---
# This helper function ensures we have a consistent way to get the client
def get_qdrant_client() -> qdrant_client.QdrantClient:
    """Initializes and returns a Qdrant client instance."""
    return qdrant_client.QdrantClient(path=QDRANT_PATH)

# --- Service Function 1: File Processing ---
async def process_and_index_file(file_content: bytes, filename: str):
    """
    Saves a file temporarily, loads its content, adds metadata, and indexes it into the Qdrant vector store.
    """
    logger.info(f"Starting processing for file: {filename}")
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, filename)

        # Save the uploaded file content to the temporary path
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Load the document from the temporary file
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        
        # **Critical Step**: Add the filename as metadata to each document chunk
        for doc in documents:
            doc.metadata["file_name"] = filename
        
        logger.info(f"Loaded {len(documents)} chunks from {filename}. Adding to vector store...")

        # Initialize the vector store and storage context
        client = get_qdrant_client()
        vector_store = QdrantVectorStore(client=client, collection_name=DOC_CHAT_COLLECTION)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Create or update the index with the new, metadata-tagged documents
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context,
            show_progress=True
        )
        logger.info(f"Successfully indexed '{filename}' into collection '{DOC_CHAT_COLLECTION}'.")

# --- Service Function 2: Document Listing ---
async def get_indexed_filenames() -> List[str]:
    """
    Queries the Qdrant collection to retrieve a list of all unique indexed filenames.
    """
    logger.info(f"Fetching unique filenames from collection '{DOC_CHAT_COLLECTION}'.")
    client = get_qdrant_client()
    
    # Use a set to automatically handle uniqueness
    seen_files = set()
    
    try:
        # The scroll API is efficient for iterating through all points in a collection
        response, _ = client.scroll(
            collection_name=DOC_CHAT_COLLECTION,
            limit=1000, # Adjust limit based on expected number of chunks
            with_payload=["file_name"], # Only retrieve the metadata we need
            with_vectors=False
        )
        for record in response:
            if record.payload and "file_name" in record.payload:
                seen_files.add(record.payload["file_name"])
    except Exception as e:
        # This can happen if the collection doesn't exist yet
        logger.warning(f"Could not scan collection '{DOC_CHAT_COLLECTION}', it may be empty. Error: {e}")
        return []
        
    logger.info(f"Found {len(seen_files)} unique filenames.")
    return sorted(list(seen_files))

# --- Service Function 3: Agent Creation ---
async def create_document_agent(selected_filenames: List[str], course: str, field: str) -> AgentRunner:
    """
    Creates and returns a LlamaIndex AgentRunner configured to query ONLY the selected documents,
    using a dynamically selected system prompt based on the user's course.
    """
    if not selected_filenames:
        raise ValueError("At least one filename must be selected to create a document agent.")

    logger.info(f"Creating document agent for {course} - {field} with files: {selected_filenames}")


    # **Important**: Configure LlamaIndex settings within the service
    # This ensures the agent uses the correct models, separate from the main app's settings.
    Settings.llm = OpenAI(model="gpt-4.1-mini")
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

    client = get_qdrant_client()
    vector_store = QdrantVectorStore(client=client, collection_name=DOC_CHAT_COLLECTION)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    
    # **Core Logic**: Build a metadata filter that accepts multiple documents
    individual_filters = [
        ExactMatchFilter(key="file_name", value=fname) 
        for fname in selected_filenames
    ]
    # The OR condition ensures chunks from ANY of the selected files are retrieved
    filters = MetadataFilters(filters=individual_filters, condition=FilterCondition.OR)
    
    # Create the two query engines (vector search and summary), both using the same filter
    vector_query_engine = index.as_query_engine(filters=filters)
    summary_query_engine = index.as_query_engine(response_mode="tree_summarize", filters=filters)

    # Create the tools for the agent
    vector_tool = QueryEngineTool(
        query_engine=vector_query_engine,
        metadata=ToolMetadata(
            name="vector_search_tool",
            description=f"Use for specific questions about the content of: {selected_filenames}"
        ),
    )
    summary_tool = QueryEngineTool(
        query_engine=summary_query_engine,
        metadata=ToolMetadata(
            name="summary_tool",
            description=f"Use to summarize or answer high-level questions about: {selected_filenames}"
        ),
    )

    # --- PROMPT INTEGRATION ---
    # Instead of a static f-string, we now call your function from _prompts.py
    system_prompt = get_system_prompt(course=course, field=field)
    
    # We can add a fallback note to the prompt so it knows how to handle documents
    # This is a good practice to combine your specific persona with the document-handling task.
    final_prompt = system_prompt + f"""
    
    ## Document Task
    You MUST base your answers ONLY on the information within the document(s): {selected_filenames}.
    If the answer is not in the documents, state: "Based on the provided text, I could not find an answer to that question."
    """

    # --- AGENT CREATION ---
    # The rest of the agent creation logic remains the same, but uses the new prompt
    agent = AgentRunner.from_llm(
        tools=[vector_tool, summary_tool], # Assuming vector_tool and summary_tool are created as before
        llm=Settings.llm,
        system_prompt=final_prompt, # Use the final, combined prompt
        verbose=True
    )
    return agent
