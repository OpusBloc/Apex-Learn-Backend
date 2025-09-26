import os
import re
import logging
import json
import functools
from typing import Optional, List

# --- LlamaIndex / Qdrant Imports (NO AGENT IMPORTS) ---
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.prompts import PromptTemplate
from llama_index.core import get_response_synthesizer
import qdrant_client

logger = logging.getLogger(__name__)



# --- Mock Test Service ---

@functools.lru_cache(maxsize=1) # Simple cache to initialize only once
async def initialize_mock_test_system():
    """
    Initializes and caches a connection to Qdrant Cloud and the LlamaIndex components.
    """
    logger.info("Initializing Mock Test System...")
    
    # Configure LlamaIndex settings
    Settings.llm = OpenAI(model="gpt-4o")
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

    # --- Connect to Qdrant Cloud ---
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if not qdrant_url or not qdrant_api_key:
        raise ValueError("QDRANT_URL or QDRANT_API_KEY not found in environment.")

    client = qdrant_client.QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    vector_store = QdrantVectorStore(client=client, collection_name="previous_year_questions")
    
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=5)
    
    logger.info("Mock Test System initialized successfully.")
    return index, reranker, Settings.llm

async def generate_mock_test(subject: str, student_class: str, board: str, topic: str, question_count: int) -> list:
    """
    Orchestrates the generation of a mock test.
    """
    index, reranker, llm = initialize_mock_test_system()

    # 1. Fetch relevant PYQs from your RAG index in Qdrant Cloud
    pyq_query = f"past exam questions for {board} class {student_class} {subject} on {topic if topic else 'various topics'}"
    pyq_text = fetch_pyqs_from_rag(index, reranker, pyq_query, subject, board) # This is your existing function

    # 2. Use LLM to structure/generate the final questions
    questions = structure_and_generate_questions_with_llm(
        llm, pyq_text, subject, student_class, board, topic, question_count
    ) # This is your existing function
    
    return questions


async def evaluate_student_answers(questions: list, user_answers: dict) -> tuple[list, float]:
    _, _, llm = initialize_mock_test_system()
    
    total_score = 0.0
    graded_results = []
    
    evaluation_tasks = []
    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i), "")
        if q['question_type'] in ['FillInTheBlank', 'ShortAnswer'] and user_ans:
            # Create an async task for each LLM evaluation
            task = evaluate_answer_with_llm(llm, q['question_text'], q['answer'], user_ans)
            evaluation_tasks.append(task)
    
    # Run all LLM evaluations concurrently for better performance
    eval_results = await asyncio.gather(*evaluation_tasks)
    eval_idx = 0

    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i), "")
        correct_ans = q['answer']
        score, feedback = 0.0, "No answer provided."

        if user_ans:
            if q['question_type'] in ['FillInTheBlank', 'ShortAnswer']:
                result = eval_results[eval_idx]
                score, feedback = result.get('score', 0.0), result.get('feedback', '')
                eval_idx += 1
            else: # MCQ
                if user_ans.strip().lower() == correct_ans.strip().lower():
                    score, feedback = 1.0, "Correct!"
                else:
                    score, feedback = 0.0, "That's not quite right."
        
        total_score += score
        graded_results.append({
            "question_text": q['question_text'], "user_answer": user_ans,
            "correct_answer": correct_ans, "score": score, "feedback": feedback
        })
    
    final_score_percentage = (total_score / len(questions)) * 100 if questions else 0
    return graded_results, round(final_score_percentage, 2)

# --- Core RAG Function to Fetch PYQs ---

async def fetch_pyqs_from_rag(index, reranker, query: str, subject: str, exam: str, year: Optional[int] = None) -> str:
    """
    Queries the RAG system to get the raw text of previous year questions based on filters.
    """
    print(f"\n--- Fetching PYQs from RAG ---")
    print(f"Query: '{query}', Subject: '{subject}', Exam: '{exam}', Year: '{year}'")

    filters_list = []
    # The key in your Qdrant metadata is "exam", not "type".
    filters_list = [
        ExactMatchFilter(key="exam", value=exam)
    ]
    
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
    
    response = await query_engine.query(query)
    print("--- RAG Response Received ---")
    return str(response)

# --- LLM Functions for Question Parsing and Generation ---

async def structure_and_generate_questions_with_llm(
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

    response_str = str(await llm.complete(prompt))
    
    try:
        json_match = re.search(r'\[.*\]', response_str, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            return []
    except json.JSONDecodeError:
        print(f"Error: LLM did not return valid JSON. Response: {response_str}")
        return []
    
    
async def evaluate_answer_with_llm(llm: OpenAI, question: str, correct_answer: str, user_answer: str) -> dict:
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
    
    response_str = str(await llm.complete(prompt))
    
    try:
        return json.loads(response_str)
    except json.JSONDecodeError:
        print(f"Error: Grader LLM did not return valid JSON. Response: {response_str}")
        # Fallback to a async default score if JSON parsing fails
        return {"score": 0.0, "feedback": "Could not automatically grade this answer."}
