import os
import re
import streamlit as st
from dotenv import load_dotenv
import logging
import json
import random
from typing import Optional

from llama_index.core import (
    VectorStoreIndex,
    Settings,
    StorageContext,
)
from llama_index.core import load_index_from_storage
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.core import get_response_synthesizer
import qdrant_client

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not found in .env file")
    st.stop()

# --- Configuration ---
QDRANT_PATH = "./qdrant_data"
QDRANT_COLLECTION_NAME = "previous_year_questions"

# --- Core RAG Function to Fetch PYQs ---

def fetch_pyqs_from_rag(index, reranker, query: str, subject: str, exam: str, year: Optional[int] = None) -> str:
    """
    Queries the RAG system to get the raw text of previous year questions based on filters.
    """
    print(f"\n--- Fetching PYQs from RAG ---")
    print(f"Query: '{query}', Subject: '{subject}', Exam: '{exam}', Year: '{year}'")

    filters_list = []
    if "cbse" in exam.lower():
        filters_list.append(ExactMatchFilter(key="type", value="cbse"))
    if subject:
        filters_list.append(ExactMatchFilter(key="subject", value=subject))
    if year:
        filters_list.append(ExactMatchFilter(key="year", value=year))
    
    final_filters = MetadataFilters(filters=filters_list)
    
    # This template instructs the LLM to just return the raw text without summarization
    VERBATIM_TEMPLATE = PromptTemplate(
        "The following is the exact text from a document. Output this text VERBATIM. "
        "Do not add any introduction, conclusion, or summary.\n\n"
        "--- CONTEXT ---\n{context_str}\n--- END CONTEXT ---"
    )

    retriever = index.as_retriever(similarity_top_k=5, filters=final_filters)
    
    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        node_postprocessors=[reranker],
        response_synthesizer=get_response_synthesizer(
            response_mode="compact", text_qa_template=VERBATIM_TEMPLATE
        ),
    )
    
    response = query_engine.query(query)
    print("--- RAG Response Received ---")
    return str(response)

# --- LLM Functions for Question Parsing and Generation ---

def structure_and_generate_questions_with_llm(
    llm: OpenAI,
    pyq_text: Optional[str],
    subject: str,
    student_class: str,
    board: str,
    topic: Optional[str],
    question_count: int
) -> list:
    """
    Uses an LLM to either:
    1. Parse existing PYQ text into a structured JSON format.
    2. Generate new questions if PYQ text is insufficient.
    
    The function aims for a mix of question types.
    """
    print("\n--- Structuring/Generating Test Questions with LLM ---")
    
    mcq_count = int(question_count * 0.5)
    fill_in_count = int(question_count * 0.3)
    short_ans_count = question_count - mcq_count - fill_in_count

    prompt = (
        f"You are an expert question paper creator for Indian schools. Your task is to create a set of {question_count} questions "
        f"for a Class {student_class} student of the {board} board, studying {subject}."
        f"The topic is '{topic if topic else 'General Syllabus'}'.\n\n"
        f"The question distribution MUST be:\n"
        f"- {mcq_count} Multiple Choice Questions (MCQs)\n"
        f"- {fill_in_count} Fill-in-the-Blank Questions\n"
        f"- {short_ans_count} Short Answer Questions (expecting a 1-2 sentence answer)\n\n"
    )

    if pyq_text and len(pyq_text.strip()) > 50:
        print("INFO: Found PYQ text. Attempting to parse and supplement.")
        prompt += (
            "You have been provided with the text of some previous year questions below. "
            "FIRST, parse these questions into the specified JSON format. "
            "SECOND, if the provided text does not yield enough questions to meet the required count for each type, "
            "you MUST generate additional questions on your own to meet the target.\n\n"
            f"--- Previous Year Question Text ---\n{pyq_text}\n\n"
        )
    else:
        print("INFO: No PYQ text provided. Generating all questions from scratch.")
        prompt += "You must generate all the questions from scratch based on the subject and class level.\n\n"

    prompt += (
        "**CRITICAL**: Your output MUST be a valid JSON list of objects. Do not include any other text or explanations.\n"
        "**ABSOLUTELY NO PLACEHOLDERS**: Do not use placeholder text like 'Generate a question...' or 'Option A'. Every question and option must be a specific, real example from the subject matter.\n"
        "Each object in the list must have the following keys:\n"
        "- `question_text`: The full text of the question.\n"
        "- `question_type`: Must be one of 'MCQ', 'FillInTheBlank', or 'ShortAnswer'.\n"
        "- `options`: A list of 4 strings for 'MCQ' type, otherwise an empty list `[]`.\n"
        "- `answer`: The correct answer string.\n\n"
        "**Example JSON output:**\n"
        "[\n"
        "  {\n"
        "    \"question_text\": \"Which part of a plant absorbs water and nutrients from the soil?\",\n"
        "    \"question_type\": \"MCQ\",\n"
        "    \"options\": [\"Leaf\", \"Stem\", \"Root\", \"Flower\"],\n"
        "    \"answer\": \"Root\"\n"
        "  },\n"
        "  {\n"
        "    \"question_text\": \"The process by which plants make their own food is called __.\",\n"
        "    \"question_type\": \"FillInTheBlank\",\n"
        "    \"options\": [],\n"
        "    \"answer\": \"Photosynthesis\"\n"
        "  }\n"
        "]"
    )

    response_str = str(llm.complete(prompt))
    
    try:
        json_match = re.search(r'\[.*\]', response_str, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            return []
    except json.JSONDecodeError:
        print(f"Error: LLM did not return valid JSON. Response: {response_str}")
        return []
    
    
def evaluate_answer_with_llm(llm: OpenAI, question: str, correct_answer: str, user_answer: str) -> dict:
    """
    Uses an LLM to evaluate if a user's answer is semantically correct,
    ignoring minor spelling or grammatical errors.
    """
    prompt = (
        f"You are an expert teacher evaluating a student's answer. Your task is to perform a semantic comparison.\n"
        f"**Question:** {question}\n"
        f"**Correct Answer:** {correct_answer}\n"
        f"**Student's Answer:** {user_answer}\n\n"
        "**Instructions:**\n"
        "1. Ignore minor spelling mistakes (e.g., 'sinee' instead of 'sine').\n"
        "2. Focus on the core meaning. Is the student's understanding correct?\n"
        "3. Determine a score: 1.0 for a correct or mostly correct answer, 0.5 for a partially correct answer that shows some understanding but is incomplete, and 0.0 for an incorrect answer.\n"
        "4. Provide one sentence of brief, encouraging feedback.\n\n"
        "**CRITICAL**: Respond ONLY with a valid JSON object in the format: "
        "{\"score\": [score], \"feedback\": \"[your feedback]\"}\n\n"
        "**Example:**\n"
        "{\"score\": 1.0, \"feedback\": \"Excellent! You've correctly identified the key concept.\"}"
    )
    
    response_str = str(llm.complete(prompt))
    
    try:
        return json.loads(response_str)
    except json.JSONDecodeError:
        print(f"Error: Grader LLM did not return valid JSON. Response: {response_str}")
        # Fallback to a default score if JSON parsing fails
        return {"score": 0.0, "feedback": "Could not automatically grade this answer."}
    
# --- System Initialization ---
@st.cache_resource
def initialize_system():
    """Initialize the RAG system by loading the index and reranker."""
    try:
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=api_key)
        llm = OpenAI(model="gpt-4-turbo-preview", api_key=api_key)

        logger.info("Connecting to local Qdrant instance...")
        client = qdrant_client.QdrantClient(path=QDRANT_PATH)
        vector_store = QdrantVectorStore(client=client, collection_name=QDRANT_COLLECTION_NAME)
        
        logger.info("Loading storage context and index from disk...")
        storage_context = StorageContext.from_defaults(vector_store=vector_store, persist_dir="./storage")
        index = load_index_from_storage(storage_context)
        
        logger.info("Initializing SentenceTransformerRerank model...")
        reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=5)
        
        logger.info("System initialized successfully.")
        return index, reranker, llm
    except Exception as e:
        st.error(f"Failed to initialize the system: {str(e)}")
        logger.error(f"Initialization error: {str(e)}", exc_info=True)
        st.stop()

# --- Streamlit UI ---

# Initialize session state variables
if "questions" not in st.session_state:
    st.session_state.questions = []
if "test_submitted" not in st.session_state:
    st.session_state.test_submitted = False
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}

st.title(" Interactive Mock Test Generator")
st.write("Select your criteria to generate a mock test. The test will prioritize questions from past papers.")


# --- INITIALIZE CORE COMPONENTS ---
rag_index, reranker_model, llm_instance = initialize_system()

# --- UI for Test Generation ---
with st.sidebar:
    st.header("⚙️ Test Configuration")
    with st.form("test_config_form"):
        board = st.selectbox("Board", ["CBSE", "ICSE"])
        student_class = st.selectbox("Class", [f"{i}" for i in range(5, 13)])
        subject = st.text_input("Subject", "Science")
        topic = st.text_input("Topic (Optional)", help="Leave blank to cover the general syllabus")
        q_count = st.number_input("Number of Questions", min_value=5, max_value=20, value=10, step=1)
        
        generate_test_button = st.form_submit_button("🚀 Generate Test")
        
rag_index, reranker_model, llm_instance = initialize_system()

if generate_test_button:
    with st.spinner("Generating your interactive test... This might take a moment."):
        # Reset previous test state
        st.session_state.questions = []
        st.session_state.test_submitted = False
        st.session_state.user_answers = {}

        # 1. Fetch PYQs from RAG
        pyq_query = f"past exam questions for {board} class {student_class} {subject} on {topic if topic else 'various topics'}"
        pyq_text_result = fetch_pyqs_from_rag(
            index=rag_index, reranker=reranker_model, query=pyq_query, subject=subject, exam=board
        )
        
        # 2. Structure/Generate questions using LLM
        generated_questions = structure_and_generate_questions_with_llm(
            llm=llm_instance,
            pyq_text=pyq_text_result,
            subject=subject,
            student_class=student_class,
            board=board,
            topic=topic,
            question_count=q_count
        )

        if generated_questions:
            st.session_state.questions = generated_questions
            st.success(f"Generated {len(generated_questions)} questions! The test is ready below.")
        else:
            st.error("Sorry, I was unable to generate a test with the given criteria. Please try again.")

# --- Display the Interactive Test ---
if st.session_state.questions and not st.session_state.test_submitted:
    st.header("📝 Your Mock Test")
    
    with st.form("interactive_test_form"):
        for i, q in enumerate(st.session_state.questions):
            st.subheader(f"Question {i+1}")
            st.markdown(q['question_text'])
            
            q_type = q['question_type']
            if q_type == 'MCQ':
                options = q['options']
                random.shuffle(options) # Shuffle options for variety
                st.session_state.user_answers[i] = st.radio(
                    "Select your answer:", options, key=f"q_{i}", index=None
                )
            elif q_type == 'FillInTheBlank':
                st.session_state.user_answers[i] = st.text_input("Your answer:", key=f"q_{i}")
            elif q_type == 'ShortAnswer':
                st.session_state.user_answers[i] = st.text_area("Your answer:", key=f"q_{i}")
            
            st.divider()

        submit_button = st.form_submit_button("Submit Test")

        if submit_button:
            st.session_state.test_submitted = True
            st.rerun()

# --- Display Results After Submission ---
if st.session_state.test_submitted:
    st.header("📊 Test Results")
    
    total_score = 0.0
    max_score = len(st.session_state.questions)
    
    # Use a spinner while the AI grades the answers
    with st.spinner("🤖 Our AI teacher is grading your answers..."):
        for i, q in enumerate(st.session_state.questions):
            user_ans = st.session_state.user_answers.get(i, "")
            correct_ans = q['answer']
            
            # Smart evaluation for open-ended questions
            if q['question_type'] in ['FillInTheBlank', 'ShortAnswer']:
                if user_ans: # Only grade if an answer was provided
                    eval_result = evaluate_answer_with_llm(
                        llm=llm_instance,
                        question=q['question_text'],
                        correct_answer=correct_ans,
                        user_answer=user_ans
                    )
                    score = eval_result.get('score', 0.0)
                    feedback = eval_result.get('feedback', '')
                else:
                    score = 0.0
                    feedback = "No answer was provided."

            # Simple comparison for MCQs
            else: # MCQ
                if user_ans and user_ans.strip().lower() == correct_ans.strip().lower():
                    score = 1.0
                    feedback = "Correct!"
                else:
                    score = 0.0
                    feedback = "That's not quite right."

            total_score += score
            
            # Store results to display after grading is complete
            q['user_score'] = score
            q['feedback'] = feedback

    # Display graded results
    for i, q in enumerate(st.session_state.questions):
        with st.container(border=True):
            st.markdown(f"**Q{i+1}:** {q['question_text']}")
            user_ans = st.session_state.user_answers.get(i, "No answer")
            st.write(f"Your answer: `{user_ans}`")

            if q['user_score'] == 1.0:
                st.success(f"✔️ Correct ({q['feedback']})")
            elif q['user_score'] == 0.5:
                st.warning(f"⚠️ Partially Correct ({q['feedback']})")
                st.info(f"**Suggested Answer:** {q['answer']}")
            else:
                st.error(f"❌ Incorrect ({q['feedback']})")
                st.info(f"**Correct Answer:** {q['answer']}")
    
    st.subheader(f"Your Final Score: {total_score} / {max_score}")
    
    if st.button("Try a New Test"):
        # Clear state to allow a new test to be generated
        st.session_state.questions = []
        st.session_state.test_submitted = False
        st.session_state.user_answers = {}
        st.rerun()