import os
import streamlit as st
from dotenv import load_dotenv
import logging

from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
from llama_index.core.agent import AgentRunner
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import Settings
from llama_index.core import ListIndex
import qdrant_client
from googleapiclient.discovery import build
from typing import List
from pydantic import BaseModel, Field
from llama_index.core.prompts import PromptTemplate


# --- PYDANTIC MODELS FOR QUIZ GENERATION ---

class QuizQuestion(BaseModel):
    """Data model for a single NEET-style multiple-choice question."""
    question: str = Field(description="The full text of the quiz question.")
    options: List[str] = Field(description="A list of 4 potential answers (A, B, C, D).")
    correct_answer: str = Field(description="The single correct answer, matching one of the options exactly.")
    explanation: str = Field(description="A brief but detailed explanation for why this is the correct answer.")

class QuizContainer(BaseModel):
    """A container data model that holds a list of quiz questions."""
    questions: List[QuizQuestion]

# --- Setup ---
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
except Exception as e:
    st.error(f"Error loading environment variables: {str(e)}")
    st.stop()

# # --- Llama-Index and Qdrant Configuration ---
# QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
# QDRANT_COLLECTION_NAME = "previous_year_questions"

# --- Llama-Index and Qdrant Configuration ---
QDRANT_PATH = "./qdrant_data" # Point to the same local storage path
QDRANT_COLLECTION_NAME = "mbbs_prep"

# --- DEFINE THE SYSTEM PROMPT ---
SYSTEM_PROMPT = """
# Identity & Tone
You are an expert AI coach for the NEET (National Eligibility cum Entrance Test) exam. Your persona is that of a highly knowledgeable, patient, and motivating Indian tuition teacher who specializes in preparing NEET aspirants, including post-12th "dropper" batches, for top ranks. Your tone is approachable, precise, encouraging, and designed to inspire students by connecting NEET concepts to their future as doctors, using a light MBBS touch to motivate without introducing out-of-syllabus content.

Your focus is strictly on Physics, Chemistry, Biology (Botany & Zoology),as defined by the official NEET syllabus (NCERT-based). Provide detailed, systematic explanations tailored to NEET’s multiple-choice question (MCQ) format, ensuring clarity for both foundational and advanced syllabus topics. Incorporate subtle MBBS-related examples (e.g., enzymes in digestion for MBBS Biochemistry) to show how NEET knowledge applies to medical practice, keeping strictly within the syllabus.

# Initial Interaction
- Assume the user is a NEET aspirant (post-12th or dropper) preparing for the exam.
- The user WILL select a subject (Physics, Chemistry, or Biology) at the start of the session. This context will be provided with their query (e.g., "[Subject Context: Physics]"). You MUST answer all questions strictly within this given subject context.
- If the query is vague (e.g., "explain osmosis"), ask if the user wants a Physics, Chemistry, or Biology explanation and confirm if they prefer a specific subtopic or NEET-style MCQ focus.
- If the user mentions "previous year papers" or "PYQs," use the `previous_year_question_engine` tool to retrieve relevant questions and provide detailed solutions if requested.

## Core Rules (Strictly Enforce)
- Answer ONLY questions related to the official NEET syllabus (Physics, Chemistry, Biology, per NCERT).
- If the selected subject is "Hindi," generate the entire response in Hindi.
- For every NEW CONCEPT explanation, you have to follow the five-part structure below. Use creative, conversational, student-friendly headings for each part (vary headings for engagement). Ensure explanations are detailed, systematic, NCERT-aligned, and exam-oriented, with a light MBBS touch to motivate aspirants. Avoid any out-of-syllabus content (e.g., induced fit model for enzymes).
- Before starting the five-part explanation, provide the topic heading in bold letters.
- **Self-Correct**: If the response includes non-NEET content (e.g., MBBS-specific topics like molecular pathways), immediately correct by stating: “Sorry, that’s beyond NEET scope. Let’s focus on the syllabus.”
- Always use this 5-part approach to provide explanation of any topic.

1. **Part 1: The Real-World Connection** (in bold)
   - **Example Headings**: "Let’s See It in Action," "Why This Matters in Life," "Your First Step to MBBS." (Vary)
   - **Content**: Use a simple, relatable real-life analogy to build intuition (e.g., enzymes as chefs). Include a brief, NCERT-appropriate connection to medical practice (e.g., “enzymes help doctors understand digestion”) to inspire students, ensuring it aligns with NEET syllabus.

2. **Part 2: The Visual Aid**(in bold)
   - **Example Headings**: "Picture the Concept," "Let’s Look at the Diagram," "Visualizing Your MBBS Foundation." (Vary)
   - **CRITICAL TOOL-USE RULE**: Use the `image_search` tool to retrieve a relevant diagram or photo URL specific to the NEET syllabus and continue your explanation as rest of the remaining parts (e.g., "labeled diagram of plant cell for NEET," "graph of SHM for NEET"). If the tool fails, describe a standard NCERT diagram and its relevance.
   - **Tool Input**: Query must be specific and NCERT-aligned (e.g., "lock and key model diagram for NEET").
   - **Content**: Briefly explain how the image clarifies the concept and its relevance to NEET or a simple medical context (e.g., “this diagram helps you ace NEET and understand MBBS Biochemistry”).

3. **Part 3: The Core Definition and Key Details**(in bold)
   - **Example Headings**: "The Textbook Lowdown," "NEET Essentials: Key Formulas," "Building Your MBBS Base." (Vary)
   - **Content**: Provide the official NCERT textbook definition (*in italics*), followed by all key formulas, laws, diagrams, or concepts critical for NEET. Include mnemonics, shortcuts, and exam tips (e.g., common MCQ traps) to aid retention and exam success. Add a brief note on how the concept connects to MBBS (e.g., “enzymes are key to MBBS Biochemistry”) without introducing non-NEET content.

4. **Part 4: NEET-Style Solved Example**(in bold)
   - **Example Headings**: "Tackling an MCQ," "Let’s Solve a Problem," "Cracking a NEET Question." (Vary)
   - **Content**: Provide a NEET-style MCQ (numerical for Physics/Chemistry, conceptual for Biology) with a step-by-step solution. Highlight common traps, time-saving techniques, and NCERT-specific connections. Include a simple medical application (e.g., “enzymes in digestion”) to motivate students.

5. **Part 5: The Understanding Check**(no heading)
   - **CRITICAL FORMATTING RULE**: This part MUST NOT have a heading.
   - **Content**: Ask, "Does this make sense, or should I explain it another way?" followed by one short, NEET-style MCQ (NCERT-aligned, conceptual or numerical) without providing the answer unless requested. Optionally, frame the MCQ with a medical context (e.g., “How does this apply to digestion in MBBS?”) to inspire.

- **Tool Call is Not the Final Answer**: When you call a tool (like `image_search` or `previous_year_question_engine`), that is only ONE STEP of your process. After the tool returns its information (like an image URL or question text), you MUST integrate that information and **continue generating the rest of your response** (such as completing Parts 3, 4, and 5 of the explanation) all in the same single answer.
- **No Outside Knowledge**: Limit responses to the NEET syllabus (NCERT-based). If a question is out of scope (e.g., engineering, arts, MBBS-specific topics like Pathology), state: "I’m focused on NEET Physics, Chemistry, Biology,  to prepare for your MBBS journey. Could you ask about a NEET syllabus topic?"
- **No Inventing**: Do not invent or assume content. Use verified NEET syllabus content from NCERT or standard sources (e.g., HC Verma for Physics).
- **Self-Correction**: If an explanation deviates from the five-part structure, NEET focus, or includes non-syllabus content, self-correct and re-align.

# Visual Aids & Image Generation
- For queries mentioning "image," "picture," "diagram," "illustration," "draw," or "show me," use the `image_search` tool to retrieve an NCERT-aligned visual.
- Prioritize clear, NCERT-based diagrams (e.g., "animal cell diagram for NEET," "V-T graph for ideal gas"). Mention how the visual relates to NEET and a simple MBBS context (e.g., “this diagram is your foundation for MBBS Physiology”).
- If the user requests an image without specifying, clarify if they want a diagram or graph relevant to the NEET topic.

# Math Formatting — Plaintext/Unicode ONLY (NO LATEX)
- **NO LATEX EVER** (e.g., \frac, \times, \overline, ^{}, \sqrt{} breaks responses). Use plaintext/Unicode.
- Exponents: Unicode (², ³, ⁴) for numbers; "to the power n" for variables (e.g., x to the power n).
- Inverse trig: Use (sin⁻¹x).
- Fractions: (x² - y²) / (x² + y²).
- Multiplication: Space or · (e.g., 2 · x · y).
- Roots: √(...), ∛(...).
- **Self-check**: If LaTeX detected, warn: “LaTeX avoided, using plaintext.” Ensure 100% plaintext/Unicode.

# Engagement
- Include quick, NCERT-aligned MCQs to reinforce learning and mimic NEET’s exam format.
- Confirm: "Does this make sense, or should I explain differently?"
- For NEET PYQs, use the `previous_year_question_engine` tool and provide detailed, step-by-step solutions if requested, highlighting exam strategies and linking to simple medical relevance for motivation (e.g., “this helps you understand digestion in MBBS”).
- End with: "Need more practice questions, a different NEET topic, a PYQ, or inspiration for your MBBS journey?"

# Quiz Generation
- After successfully explaining a concept, you should offer the user a short, adaptive quiz on that topic.
- If the user agrees (e.g., "yes," "quiz me," "sounds good"), you MUST call the `initiate_adaptive_quiz` tool.
- You MUST provide both the general 'subject' and the specific 'topic' of the concept just explained.
"""

@st.cache_resource
def initialize_system():
    """Initialize all the necessary components for the RAG system."""
    try:
        # --- UPDATE THE LLM INITIALIZATION ---
        Settings.llm = OpenAI(
            model="gpt-4.1-mini", 
            api_key=api_key, 
        )
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=api_key)

        client = qdrant_client.QdrantClient(path=QDRANT_PATH)
        vector_store = QdrantVectorStore(client=client, collection_name=QDRANT_COLLECTION_NAME)
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

        # --- Tool 1:RAG Query Engine ---
        vector_retriever = index.as_retriever(similarity_top_k=10)
        reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=3)
        response_synthesizer = get_response_synthesizer(response_mode="compact")
        rag_query_engine = RetrieverQueryEngine(
            retriever=vector_retriever,
            response_synthesizer=response_synthesizer,
            node_postprocessors=[reranker]
        )
        rag_tool = QueryEngineTool(
            query_engine=rag_query_engine,
            metadata=ToolMetadata(
                name="previous_year_question_engine",
                description=(
                    "Use this tool ONLY when the user asks for Previous Year Questions (PYQs), past papers, or specific questions from past NEET, AIIMS, or AIMPT exams. "
                    "This tool searches a database of old exam questions. Do NOT use it for general concept explanations."
                )
            ),
        )
        
        # --- Tool 2: LLM-Only Query Engine ---
        empty_index = ListIndex([])
        llm_query_engine = empty_index.as_query_engine(response_mode="generation")
        llm_tool = QueryEngineTool(
            query_engine=llm_query_engine,
            metadata=ToolMetadata(
                name="textbook_knowledge_engine",
                description=(
                    "The primary tool for explaining all NEET-level concepts in Physics, Chemistry, and Biology. "
                    "Use this to define terms, explain mechanisms, formulas, or any general academic question related to the NEET syllabus. "
                    "Use this by default unless the user specifically asks for a PYQ or an image."
                )
            ),
        )
        
        # --- IMAGE RETRIEVAL WEB ------
        def search_web_for_image(query: str) -> str:
            """
            Searches the web for an image using the Google Custom Search API,
            and cycles through results to avoid repetition on the same query.
            """
            print(f"\n--- TOOL CALLED [IMAGE SEARCH] ---")
            print(f"Original Query: '{query}'")
            try:
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key or not cse_id:
                    return "Error: Google API credentials are not configured."
                
                # Get the history and update the count for this query
                query_count = st.session_state.image_search_history.get(query, 0)
                st.session_state.image_search_history[query] = query_count + 1

                # Use the count to fetch a different result from the top 5 images.
                # The start index for Google API is 1-based.
                start_index = 1 + (query_count % 5)
                print(f"Fetching result number {start_index} for this query to ensure variety.")
                # --- END MODIFICATION ---

                service = build("customsearch", "v1", developerKey=api_key)
                res = service.cse().list(
                    q=query,
                    cx=cse_id,
                    searchType='image',
                    num=1,
                    start=start_index,  # Use the calculated start index for variety
                    safe='high'
                ).execute()
                
                if 'items' in res and len(res['items']) > 0:
                    image_url = res['items'][0]['link']
                    return image_url  # <-- CHANGED
                else:
                    # Fallback...
                    if start_index > 1:
                        print(f"Fallback: No result at index {start_index}. Trying the top result.")
                        res_fallback = service.cse().list(q=query, cx=cse_id, searchType='image', num=1, start=1, safe='high').execute()
                        if 'items' in res_fallback and len(res_fallback['items']) > 0:
                            return res_fallback['items'][0]['link'] # <-- CHANGED
                    return "Could not find a suitable image for that query."

                # if 'items' in res and len(res['items']) > 0:
                #     image_url = res['items'][0]['link']
                #     return f"IMAGE_URL::{image_url}"
                # else:
                #     # Fallback: If we're past the first result and find nothing, try the first result again.
                #     if start_index > 1:
                #         print(f"Fallback: No result at index {start_index}. Trying the top result.")
                #         res_fallback = service.cse().list(q=query, cx=cse_id, searchType='image', num=1, start=1, safe='high').execute()
                #         if 'items' in res_fallback and len(res_fallback['items']) > 0:
                #             return f"IMAGE_URL::{res_fallback['items'][0]['link']}"
                #     return "Could not find a suitable image for that query."

            except Exception as e:
                logger.error(f"Google Image Search Error: {e}", exc_info=True)
                return f"Error searching for image: {str(e)}"
            
            
        # --- (Inside initialize_system(), right before the IMAGE RETRIEVAL section) ---
        
        # --- ADAPTIVE QUIZ FUNCTION STUBS ---
        # These are placeholders. You must implement their real logic.
        
        def get_weakest_topics(profile: dict, subject: str, count: int) -> list:
            """
            STUB FUNCTION: Replace this with your logic to get weak topics 
            from the performance_profile session state.
            """
            print("[STUB] get_weakest_topics called. Returning placeholder topics.")
            # Placeholder logic:
            if subject == "Biology":
                return ["Cell Structure", "Genetics"]
            return ["Motion", "Forces"]


        def generate_interactive_test_with_llm(llm, subject, student_class, question_count, focus_topics, difficulty_mix) -> list:
            """
            REAL FUNCTION: Calls the LLM to generate a structured list of quiz questions
            by forcing the output into our Pydantic schema.
            """
            print(f"[REAL FUNCTION] Generating {question_count} questions for topics: {focus_topics}")

            # Combine the topics into a clean string for the prompt
            topics_string = ", ".join(focus_topics)
            
            # This is the new, specific prompt template to generate the quiz
            # It instructs the LLM on its role and the exact format required.
            quiz_prompt_template_str = """
            You are an expert NEET AI Coach and exam question creator.
            Your task is to generate {count} high-quality, NEET-style multiple-choice questions.

            RULES:
            - Subject: {subject}
            - Main Topics: {topics}
            - All questions MUST be 100% aligned with the NCERT syllabus for NEET.
            - Options must be plausible, and explanations must be clear, concise, and scientific.
            - Ensure the 'correct_answer' text EXACTLY matches one of the strings in the 'options' list.
            - Do not include any questions on out-of-syllabus topics (like the 'induced fit model').

            Generate the quiz now.
            """
            
            prompt_template = PromptTemplate(quiz_prompt_template_str)

            try:
                
                response = llm.structured_predict(
                    QuizContainer,  # The Pydantic class we want it to fill
                    prompt_template,  # The prompt template to use
                    subject=subject,
                    topics=topics_string,
                    count=question_count
                )
          
                
                question_list_of_dicts = [q.model_dump() for q in response.questions]
                
                if not question_list_of_dicts:
                    raise ValueError("LLM returned an empty question list.")

                print(f"Successfully generated {len(question_list_of_dicts)} real questions.")
                return question_list_of_dicts

            except Exception as e:
                logger.error(f"Error in REAL quiz generation: {e}", exc_info=True)
                # Fallback to a placeholder if the structured generation fails
                return [
                    {
                        "question": "Sorry, I had an error generating a real question. This is a fallback.",
                        "options": ["Option A", "Option B (Error)", "Option C", "Option D"],
                        "correct_answer": "Option B (Error)",
                        "explanation": f"The generation failed with: {e}"
                    }
                ]
            
        # --- YOUR NEW TOOL FUNCTION DEFINITION ---
        def initiate_adaptive_quiz(subject: str, topic: str) -> str:
            """
            Initiates a short, adaptive quiz for the user on a specific topic.
            This tool should be called by the agent after getting the user's consent.
            Requires the current 'subject' and the specific 'topic' of the lesson.
            """
            print(f"\n--- TOOL CALLED [ADAPTIVE QUIZ GENERATOR] for Subject: {subject}, Topic: {topic} ---")
            
            # 1. The conversational topic is the highest priority "seed" for the quiz.
            seed_topic = topic

            # 2. Check the profile for other weak topics to potentially mix in.
            weak_topics_from_profile = get_weakest_topics(
                profile=st.session_state.performance_profile, 
                subject=subject, 
                count=2
            )

            # 3. Build the final list of topics.
            focus_topics = [seed_topic]
            for t in weak_topics_from_profile:
                if t.lower() != seed_topic.lower() and len(focus_topics) < 3:
                    focus_topics.append(t)
    
            print(f"Quiz generator focusing on topics: {', '.join(focus_topics)}")

            # 4. Directly call the question generator (Using Settings.llm as the instance)
            quiz_questions = generate_interactive_test_with_llm(
                llm=Settings.llm,  # Using the LLM from our Settings
                subject=subject,
                student_class="12", # Hardcoded for NEET context
                question_count=2,   # Keeping the stub quiz short
                focus_topics=focus_topics,
                difficulty_mix={'Easy': 1, 'Medium': 1} 
            )

            if not quiz_questions:
                return "I'm sorry, I had a little trouble creating a quiz on that specific topic right now. Let's continue our lesson."

            # 5. Set up the quiz state.
            st.session_state.current_test = quiz_questions
            st.session_state.current_question_index = 0
            st.session_state.conversation_mode = "quiz" # This is the critical state change
            st.session_state.quiz_responses = [] # To track answers
    
            # This response goes back to the LLM, not the user. The UI will change based on the state.
            return f"A {len(quiz_questions)}-question quiz on {', '.join(focus_topics)} has been generated. The UI will now display the first question."
        
        # --- (Your IMAGE RETRIEVAL WEB section comes next) ---
            
            # This creates the tool object that the agent can use.
        image_retrieval_tool = FunctionTool.from_defaults(
            fn=search_web_for_image,
            name="image_search",
            description=(
                "Use this tool as part of explnation or when the user explicitly asks for a visual image, "
                "diagram, photo, illustration, or map. Use for requests like: "
                "'draw a diagram of...', 'show me a picture of...', 'find an image of...', etc."
                "whenever explaining a new concept, use this tool as a part of 5-part explanation"
            )
        )
        
        # --- Tool 3: Adaptive Quiz Tool ---
        quiz_tool = FunctionTool.from_defaults(
            fn=initiate_adaptive_quiz,
            name="initiate_adaptive_quiz",
            description=(
                "Use this tool to create and start an adaptive quiz for the user. "
                "This should only be called AFTER the user agrees to take a quiz. "
                "You must pass the current 'subject' (e.g., 'Biology') and the specific 'topic' just discussed (e.g., 'Enzyme Action')."
            )
        )

        all_tools = [rag_tool, image_retrieval_tool, quiz_tool]
        agent = AgentRunner.from_llm(
            tools=all_tools,
            llm=Settings.llm,  
            system_prompt=SYSTEM_PROMPT, 
            verbose=True  # Setting verbose=True is great for debugging in your terminal
        )
        
        return agent 

    except Exception as e:
        st.error(f"Failed to initialize the RAG system: {str(e)}")
        logger.error(f"Initialization error: {str(e)}", exc_info=True)
        st.stop()

# --- Streamlit UI ---
st.title("NEET AI Prep Coach")
st.write("Ask me to explain any concept from Physics, Chemistry, or Biology, or test you with Previous Year Questions (PYQs)!")

# Initialize system
query_engine = initialize_system()

# --- CLEAN UP SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Namaste! I'm your dedicated NEET coach. We can cover any concept from Physics, Chemistry, or Biology, or practice PYQs. What topic is on your mind today?"
        }
    ]
if "image_search_history" not in st.session_state:
    st.session_state.image_search_history = {}
if "subject_selected" not in st.session_state:
    st.session_state.subject_selected = None
if "conversation_mode" not in st.session_state:
    st.session_state.conversation_mode = "chat"  # Default mode is chat
if "current_test" not in st.session_state:
    st.session_state.current_test = []
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "quiz_responses" not in st.session_state:
    st.session_state.quiz_responses = []
if "performance_profile" not in st.session_state:
    st.session_state.performance_profile = {} # Your quiz logic will populate this
if "show_quiz_feedback" not in st.session_state:
    st.session_state.show_quiz_feedback = None

# Display conversation history
# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- MODE-BASED UI LOGIC ---
# ===================================================================
# STATE 1: QUIZ MODE (REVISED LOGIC)
# ===================================================================
if st.session_state.conversation_mode == "quiz":
    
    # Check if the quiz is valid and we haven't finished
    if st.session_state.current_test and st.session_state.current_question_index < len(st.session_state.current_test):
        
        q = st.session_state.current_test[st.session_state.current_question_index]
        
        # This is the key: check if we are showing feedback OR asking the question
        if st.session_state.show_quiz_feedback:
            # --- STATE B: SHOWING FEEDBACK ---
            # We have already submitted an answer, so just show the results.
            
            feedback_data = st.session_state.show_quiz_feedback
            
            st.markdown(f"### Result for Question {st.session_state.current_question_index + 1}")
            st.markdown(f"**{q['question']}**")
            
            # Show the user's selected answer (you can format this however you like)
            st.write(f"*Your answer: {feedback_data['selected']}*")

            # Display the correct/incorrect message AND the explanation
            if feedback_data['is_correct']:
                st.success(f"Correct! \n\n*Explanation: {q['explanation']}*")
            else:
                st.error(f"Not quite. The correct answer is **{q['correct_answer']}**. \n\n*Explanation: {q['explanation']}*")
            
            # Now show the button to advance
            if st.button("Next Question"):
                st.session_state.current_question_index += 1 # Advance index
                st.session_state.show_quiz_feedback = None # Reset feedback state
                st.rerun() # Rerun to show next question or summary

        else:
            # --- STATE A: ASKING THE QUESTION ---
            # This is the default state: show the question and options.
            st.markdown(f"### Question {st.session_state.current_question_index + 1} of {len(st.session_state.current_test)}")
            st.markdown(f"**{q['question']}**")
            
            user_answer = st.radio(
                "Select your answer:",
                q['options'],
                index=None,
                key=f"quiz_q_{st.session_state.current_question_index}"
            )
            
            if st.button("Submit Answer"):
                if user_answer:
                    # User submitted. Store the response...
                    st.session_state.quiz_responses.append({
                        "question": q['question'],
                        "selected": user_answer,
                        "correct": q['correct_answer'],
                        "explanation": q['explanation']
                    })
                    
                    # (This is where you would update the performance_profile)

                    # ...NOW, INSTEAD OF ADVANCING, just store feedback data...
                    st.session_state.show_quiz_feedback = {
                        "selected": user_answer,
                        "is_correct": user_answer == q['correct_answer']
                    }
                    
                    # ...and rerun to trigger STATE B (showing feedback).
                    st.rerun()
                else:
                    st.warning("Please select an answer.")
    
    else:
        # Quiz is over (This logic was correct)
        st.success("Quiz complete!")
        # ... (rest of your quiz summary logic is fine)
        # ...
        st.session_state.conversation_mode = "chat"
        st.session_state.current_test = []
        st.session_state.quiz_responses = []
        st.session_state.show_quiz_feedback = None # Clean up feedback state

        st.session_state.messages.append({"role": "assistant", "content": "Great job on the quiz! What concept would you like to cover next?"})
        if st.button("Back to Lesson"): # Use if to avoid error on auto-rerun
            st.rerun()


# ===================================================================
# STATE 2: CHAT MODE (Your original logic)
# This only runs if we are NOT in quiz mode
# ===================================================================
elif st.session_state.conversation_mode == "chat":

    # --- Subject Selection (This logic stays the same) ---
    if not st.session_state.subject_selected:
        selected_subject = st.selectbox(
            "Please select your subject to begin:",
            ["--- Select Subject ---", "Physics", "Chemistry", "Biology"]
        )
        
        if st.button("Start Session") and selected_subject != "--- Select Subject ---":
            st.session_state.subject_selected = selected_subject
            welcome_text = f"Great! We're focusing on **{selected_subject}**. What concept can I help you with first?"
            st.session_state.messages.append({"role": "assistant", "content": welcome_text})
            st.rerun()

    # --- Main Chat Input (Only show if subject IS selected) ---
    else:
        st.caption(f"Current Session: {st.session_state.subject_selected} (Chat Mode)")
        
        user_input = st.chat_input(f"Ask your {st.session_state.subject_selected} question:")

        if user_input:
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": user_input})

            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(user_input)

            contextual_query = f"[Subject Context: {st.session_state.subject_selected}] User query: {user_input}"

                
            logger.info(f"Sending contextual query to agent: {contextual_query}")

            # Generate and display response from the agent
            try:
                with st.spinner(f"Thinking about {st.session_state.subject_selected}..."):
                    response = query_engine.chat(contextual_query)
                    response_content = str(response)

                # Add assistant's response to history
                st.session_state.messages.append({"role": "assistant", "content": response_content})

                # Display assistant's response
                with st.chat_message("assistant"):
                    st.markdown(response_content)
                
                # Rerun to clear the input box and show the full response
                st.rerun() 
                    
            except Exception as e:
                error_message = f"Sorry, an error occurred: {str(e)}"
                st.error(error_message)
                logger.error(f"Query processing error: {str(e)}", exc_info=True)
                st.session_state.messages.append({"role": "assistant", "content": error_message})