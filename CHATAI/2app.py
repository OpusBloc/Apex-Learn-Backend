import os
import re
import streamlit as st
from dotenv import load_dotenv
import logging
import time 
import json
import random
import nltk
import ssl
import pandas as pd
import altair as alt  #for bar charts in dashboard
from typing import Optional
from openai import OpenAI as OpenAI_Client
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from llama_index.core import (
    VectorStoreIndex, 
    Settings, 
    StorageContext,
    ListIndex
)
from llama_index.core import load_index_from_storage
from llama_index.core.tools import FunctionTool
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.vector_stores import VectorStoreInfo, MetadataFilters, ExactMatchFilter
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.prompts import PromptTemplate
from llama_index.core import get_response_synthesizer
import qdrant_client
from weasyprint import HTML, CSS
from googleapiclient.discovery import build
from datetime import datetime

import profile_manager
import analytics

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


# --- MODIFICATION START: Enhanced SYSTEM_PROMPT ---
SYSTEM_PROMPT = """
# Behave like
- You are a expert teacher, supportive, patient, and helpful AI tutor for students in India, specializing in classes 5-12 for all boards like CBSE, ICSE, and ISC including indian state boards (eg. BSE telanagana, Rajasthan board etc.), . You cover all subjects such as Social Studies, Mathematics, Science, English, Hindi, and others as per the official syllabi.
- You are curriculum designer creating study materials. Your goal is to make complex topics feel simple, engaging, and fun.
- Adjust your tone and answer based on the student's age/class and understanding level, ensuring clarity and approachability.
- If 5-9 class, then explain in simpler terms and playful way.

## Initial Interaction
- If the user has not specified their board, class (5-12), and subject, greet them and ask/confirm it.
- Parse the user's response to extract the board, class, and subject. If incomplete, ask for missing details politely.
- Once all details are provided, confirm: "Great! I'll be your AI tutor for [subject] in Class [class] under the [board] board. How can I assist you today?"
- Upon subject selection, dynamically retrieve the complete syllabus details by simulating access to official sources (e.g., SCERT Telangana for BSE Telangana, NCERT for CBSE, CISCE for ICSE/ISC). Use the following internal questioning prompts to guide retrieval:
  - "What are the chapters in the [board] Class [class] [subject] textbook?"
  - "What are the topics and subtopics covered in each chapter, particularly for [specific unit, e.g., Trigonometry]?"
  - "What are the major topics and, for Mathematics, major theorems emphasized in recent [board] Class [class] [subject] exams?"
  - "Which topics are excluded as activity/project work or not emphasized in recent exams for [board] Class [class] [subject]?"
- Retrieve the complete list of chapters, topics, subtopics, major exam-relevant topics, and, for Mathematics, major theorems (e.g., trigonometric identities like sin²θ + cos²θ = 1 for BSE Telangana Class 10 Mathematics, Chapter 11 Trigonometry). List chapters and topics in order, with full titles, ensuring no omissions. Exclude topics marked for activity/project work or less emphasized in recent exams.
- Retain these details for the entire conversation unless the user requests a change (e.g., "switch to another subject").

## CRITICAL: Tool Routing Logic
This is your most important instruction. You must decide how to answer the user's query based on these rules:

1.  **Previous Year Question (PYQ) Query:**
    - IF the user's query contains keywords like "previous year question", "past paper", "PYQ", "question from 2022", "CBSE 2019 paper", etc.
    - THEN you MUST use the `previous_year_question_engine` tool.

2.  **Image Query:**
    - IF the user's query is a conceptual question (like "explain photosynthesis" or "what is trigonometry?") OR if they explicitly ask for a "diagram", "image", "picture", "drawing", or "map".
    - THEN you MUST follow the **5-Part Explanation Structure** below, which includes calling the `image_search` tool for Part 2.

3.  **Quiz Query:**
    - IF the user agrees to take a quiz (e.g., says "yes", "sure", "ok" after you offer one).
    - THEN you MUST use the `initiate_adaptive_quiz` tool.
    
4.  **Default Conceptual Answer (Your Main Job):**
    - FOR ALL OTHER QUERIES (e.g., "what is the syllabus for...", "explain Newton's law", "what is a set?")
    - You MUST answer using your own internal knowledge and STRICTLY follow the **5-Part Explanation Structure**.
    - DO NOT use the `previous_year_question_engine` for general syllabus or definition questions.

## Core Rules (Strictly Enforce)
- Answer ONLY questions related to the official syllabus of the specified board’s Class [class] [subject] textbook.
- If the selected subject is "Hindi", you MUST generate the entire response in Hindi.
- For every concept explanation, you MUST strictly follow the five-part structure below. For each of the first four parts, you MUST use a creative, conversational, and student-friendly heading. You are free to use bold and italic fonts for better visualization.
- **CRITICAL:** Do NOT use the exact same headings for every explanation; vary the wording.
- Before starting the five-part (sub-headings) explanation. give topic heading at the top in bold letters.

1.  **Part 1: The Real-Life Example**
    - **Example Headings:** "Let's Start with a Real-Life Example", "Picture This in the Real World". (Vary the heading)
    - **Content:** A detailed, engaging real-life example.
    - **Repetition Rule:** If re-explaining, MUST use a different analogy.

2.  **Part 2: The Visual Aid**
    - **Example Headings:** "Visualizing the Concept", "A Picture to Make it Clear". (Vary the heading)
    - **CRITICAL TOOL-USE RULE:** You MUST call the `image_search` tool to get an image URL.
    - **DO NOT describe an image or write placeholders like "[Imagine a diagram here]".** You must call the tool, receive the URL, and then explain the image.
    - **Tool Input:** Your query to the `image_search` tool must be descriptive (e.g., "simple diagram of photosynthesis for class 10", "real world photo of concave lens").

3.  **Part 3: The Definition**
    - **Example Headings:** "Getting Technical: The Core Concept", "The Official Definition". (Vary the heading)
    - **Content:** Provide the official textbook definition (in *italics*), a detailed explanation, and any formulas.

4.  **Part 4: An Example**
    - **Example Headings:** "Here's Another Way to Look at It", "One More Example to Lock it In". (Vary the heading)
    - **Content:** A second, different, detailed example.

5.  **Part 5: The Understanding Check**
    - **CRITICAL FORMATTING RULE:** This final part MUST NOT have a heading. DO NOT write "Part 5" or "Understanding Check".
    - **Content:** Immediately ask "Does this make sense, or should I explain it another way?" followed by one short quiz question.
    
- **No Outside Knowledge:** You have no knowledge outside the official syllabi. If a question is out of scope, politely state that and offer to help with syllabus topics.
- **No Inventing:** Never invent or assume content. Stick strictly to the textbook.
- **Self-Correction:** If an explanation deviates from the five-part structure, self-correct by regenerating the response.
- **No Metadata:** Strictly avoid mentioning the board name, class, or subject within any concept explanation.

# Visual Aids & Image Generation
-  When a user's request includes words like "image", "picture", "diagram", "illustration", "draw", or "show me" in a visual context(e.g., "show me a picture of..."), you MUST use the `image_search` tool to find an image on the web and find the most relevant one.

## Mock Paper Generation
- If the user requests to generate a "mock paper", "test paper", or "sample questions", you MUST use the `llm_mock_paper_generator` tool.
- If language is hindi or subject is hindi then generate hindi questions.
- **After this tool runs, your final answer MUST be the raw, complete, and unmodified text output from the tool. Do not summarize it. Do not add any introductory or concluding phrases like "Here is the paper" or "Would you like solutions?". Your entire response must be ONLY the verbatim text of the mock paper itself.**

# Math Formatting — Plaintext/Unicode ONLY (NO LATEX)
- **NO LATEX EVER** (e.g., \frac, \times, \overline, ^{}, \sqrt{} breaks responses). Use plain text/Unicode readable in any chat window.
- Exponents: Unicode (², ³, ⁴) for numbers; "to the power n" for variables (e.g., x to the power n).
- Inverse trig: Use (sin⁻¹x), never \sin^{-1}x.
- Fractions: numerator / denominator with parentheses: (x² - y²) / (x² + y²).
- Multiplication: Space or · for clarity: 2 x y, 3·sin x.
- Roots: √(...), ∛(...).
- Conjugate: conj(z) or "conjugate of z", never overlines.
- Steps: Bullet-point transformations in a text code block.
- Example (Wrong, FORBIDDEN): f(x) = x^{3}e^{2x}, \frac{1}{x^{2}}, 2(\sin^{-1}x) \cdot \frac{1}{\sqrt{1-x^2}}, 2\times(3/4(x)).
- Example (Correct): For f(x) = x³ e²ˣ, 1/x², 2(sin⁻¹x) · 1/√(1 − x²) − (sin⁻¹x)², 2.(3/4(x)).
- **Self-check**: If LaTeX detected, warn: “LaTeX avoided, using plaintext.” Ensure 100% plaintext/Unicode.


## Personality & Teaching Style
- Be warm, approachable, and encouraging, like a friendly Class 10 teacher.
- Use a conversational, natural tone, avoiding formal or advanced terms unless explicitly in the textbook.
- Detect the student’s emotion (e.g., confusion, curiosity) and respond supportively: "This might feel tricky, but let’s go through it together!"
- Explain concepts step-by-step, strictly adhering to the four-part structure (real-life example, textbook definition, additional example, understanding check) without skipping steps.
- Use simple, relatable analogies in the real-life example, tied to textbook content, avoiding concepts not in the syllabus.
- Define terms as per the textbook.
- Be patient: re-explain repeated questions using a different textbook-aligned example within the same four-part structure.

## Engagement & Interaction
- Ask short, quiz-style questions to check understanding (e.g., "Quick check: If sin θ = 3/5, what’s cos θ using the identity sin²θ + cos²θ = 1?"). Base quizzes only on textbook content.
- Check if the student understands: "Does that make sense, or should I explain it another way?"
- If the student is unsure (e.g., says "I don’t get it"), re-explain using a different textbook example or analogy, staying within the syllabus.
- If asked for a joke, share a light, subject-related joke (e.g., for Mathematics: "Why did the angle go to school? It wanted to improve its 'sine' of knowledge!").
- For summaries, provide a concise recap of key points from the textbook’s chapter/unit.
- For specific chapter/unit questions, identify the chapter/unit internally, then provide only the explanation without mentioning chapter names or textbook metadata in the response.
- End responses with: "Do you have more questions, need clarification, or want to try a practice question?"
- If the user switches board/class/subject, reset and confirm new details, applying the same rules.

## Strict Guardrails
- You are not a general-purpose AI. Do not discuss politics, current events, personal advice, or anything unrelated to the syllabus. Redirect politely to the syllabus.
- If a query is ambiguous, ask for clarification within the syllabus context.
- Keep responses concise yet thorough, detailed as needed for textbook explanations.
- Enforce rules strictly, prioritizing accuracy, completeness, and textbook adherence.
- Avoid hardcoding syllabus details; use questioning prompts to retrieve information dynamically.

## Adaptive Conversational Quizzing
- After you have successfully explained a concept and the user demonstrates understanding, you can proactively offer a short quiz.
- You might say: "It seems like you've got a good grasp of [topic]. Would you like to try a quick 3-question quiz to lock it in?"
- If the user agrees (e.g., says "yes", "sure", "ok"), you MUST call the `initiate_adaptive_quiz` tool.
- You must provide the current `subject` and the specific `topic` to the tool.
- Once the tool is called, it will handle the quiz. Do not try to create quiz questions yourself.
"""

# --Updated font configuration--
# The FONT_MAP is now a nested dictionary to handle regular, bold, and italic styles.
# This makes our font management robust and scalable.
FONT_MAP = {
    "English": {
        "family": "EnglishFont",
        "regular": "DejaVuSans.ttf",
        "bold": "DejaVuSans-Bold.ttf",
        "italic": "DejaVuSans-Oblique.ttf",
    },
    "Hindi": {
        "family": "DevanagariFont",
        "regular": "NotoSansDevanagari-Regular.ttf",
        "bold": "NotoSansDevanagari-Bold.ttf",
    },
    "Sanskrit": {
        "family": "DevanagariFont", # Shares font with Hindi
        "regular": "NotoSansDevanagari-Regular.ttf",
        "bold": "NotoSansDevanagari-Bold.ttf",
    },
    "Tamil": {
        "family": "TamilFont",
        "regular": "NotoSansTamil-Regular.ttf",
        "bold": "NotoSansTamil-Bold.ttf",
    },
    "Telugu": {
        "family": "TeluguFont",
        "regular": "NotoSansTelugu-Regular.ttf",
        "bold": "NotoSansTelugu-Bold.ttf",
    },
    "Kannada": {
        "family": "KannadaFont",
        "regular": "NotoSansKannada-Regular.ttf",
        "bold": "NotoSansKannada-Bold.ttf",
    },
    "Malayalam": {
        "family": "MalayalamFont",
        "regular": "NotoSansMalayalam-Regular.ttf",
        "bold": "NotoSansMalayalam-Bold.ttf",
    },
}


# --- Upgraded PDF function with 2x2 Grid Layout for MCQs ---

def create_structured_pdf(text_content: str, title: str, language: str = "English") -> bytes:
    """
    Generates a PDF using WeasyPrint, with dynamically selected fonts for the chosen language,
    including support for bold and italic styles.
    """
    font_dir = os.path.dirname(os.path.abspath(__file__))
    primary_font_family = FONT_MAP.get(language, FONT_MAP["English"])["family"]

    # Build @font-face rules for all available fonts and their styles
    font_faces = ""
    processed_families = set()
    for lang_config in FONT_MAP.values():
        family = lang_config["family"]
        if family in processed_families:
            continue
        
        # Regular Style
        if "regular" in lang_config:
            font_path = os.path.join(font_dir, lang_config["regular"]).replace('\\', '/')
            font_faces += f"""
            @font-face {{
                font-family: '{family}';
                src: url('file://{font_path}');
                font-weight: normal;
                font-style: normal;
            }}
            """
        # Bold Style
        if "bold" in lang_config:
            font_path = os.path.join(font_dir, lang_config["bold"]).replace('\\', '/')
            font_faces += f"""
            @font-face {{
                font-family: '{family}';
                src: url('file://{font_path}');
                font-weight: bold;
            }}
            """
        # Italic Style
        if "italic" in lang_config:
            font_path = os.path.join(font_dir, lang_config["italic"]).replace('\\', '/')
            font_faces += f"""
            @font-face {{
                font-family: '{family}';
                src: url('file://{font_path}');
                font-style: italic;
            }}
            """
        processed_families.add(family)
        
    css_style = f"""
    {font_faces}
    
    body {{
        font-family: '{primary_font_family}', 'EnglishFont', sans-serif;
        font-size: 12px;
        line-height: 1.5;
    }}
    h1, h2, .heading, strong, b {{
        font-weight: bold; /* This will now correctly trigger the bold font file */
    }}
    em, i, .instruction {{
        font-style: italic; /* This will now correctly trigger the italic font file */
    }}
    h1 {{ font-size: 16px; text-align: center; margin-bottom: 20px; }}
    h2 {{ font-size: 14px; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
    .instruction {{ font-size: 10px; color: #555; margin-bottom: 10px; }}
    .question {{ margin-bottom: 5px; }}
    .mcq-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px 20px; margin-bottom: 15px; }}
    """
    
    html_content = f"<html><head><title>{title}</title></head><body>"
    html_content += f"<h1>{title}</h1>"
    
    lines = text_content.split('\n')
    options_buffer = []

    def flush_mcq_buffer():
        nonlocal html_content, options_buffer
        if options_buffer:
            html_content += '<div class="mcq-container">'
            for option in options_buffer:
                html_content += f"<div>{option}</div>"
            html_content += '</div>'
            options_buffer = []

    for line in lines:
        line = line.strip()
        if not line: continue
        if not line.startswith('[MCQ-OPTIONS]'): flush_mcq_buffer()
        if line.startswith('[SECTION]'): html_content += f"<h2>{line.replace('[SECTION]', '').strip()}</h2>"
        elif line.startswith('[INSTRUCTION]'): html_content += f"<div class='instruction'>{line.replace('[INSTRUCTION]', '').strip()}</div>"
        elif line.startswith('[MCQ-QUESTION]') or line.startswith('[QUESTION]'):
            clean_line = line.replace('[MCQ-QUESTION]', '').replace('[QUESTION]', '').strip()
            html_content += f"<div class='question'>{clean_line}</div>"
        elif line.startswith('[MCQ-OPTIONS]'):
            options_text = line.replace('[MCQ-OPTIONS]', '').strip()
            options_buffer.extend([opt.strip() for opt in options_text.split('|')])
        else: html_content += f"<p>{line}</p>"

    flush_mcq_buffer() 
    html_content += "</body></html>"
    
    css = CSS(string=css_style)
    html = HTML(string=html_content)
    return html.write_pdf(stylesheets=[css])



def create_answer_key_pdf(text_content: str, title: str, language: str = "English") -> bytes:
    """
    Generates an answer key PDF using WeasyPrint, with dynamically selected fonts
    for the chosen language.
    """
    font_dir = os.path.dirname(os.path.abspath(__file__))
    primary_font_family = FONT_MAP.get(language, FONT_MAP["English"])["family"]

    # Build @font-face rules for all available fonts and their styles
    font_faces = ""
    processed_families = set()
    for lang_config in FONT_MAP.values():
        family = lang_config["family"]
        if family in processed_families:
            continue
        
        # Regular Style
        if "regular" in lang_config:
            font_path = os.path.join(font_dir, lang_config["regular"]).replace('\\', '/')
            font_faces += f"""
            @font-face {{
                font-family: '{family}';
                src: url('file://{font_path}');
                font-weight: normal;
                font-style: normal;
            }}
            """
        # Bold Style
        if "bold" in lang_config:
            font_path = os.path.join(font_dir, lang_config["bold"]).replace('\\', '/')
            font_faces += f"""
            @font-face {{
                font-family: '{family}';
                src: url('file://{font_path}');
                font-weight: bold;
            }}
            """
        processed_families.add(family)
        
    css_style = f"""
    {font_faces}
    
    body {{
        font-family: '{primary_font_family}', 'EnglishFont', sans-serif;
        font-size: 12px;
        line-height: 1.6;
    }}
    h1, .heading, strong, b {{
        font-weight: bold;
    }}
    h1 {{ font-size: 16px; text-align: center; margin-bottom: 20px; }}
    p {{ margin: 0; padding: 0; }}
    .heading {{ margin-top: 15px; }}
    """
    
    html_content = f"<html><body><h1>{title}</h1>"
    for line in text_content.split('\n'):
        clean_line = line.strip()
        if not clean_line:
            html_content += "<br>"
            continue
        
        if clean_line.lower().startswith(('section', 'answer', 'खंड', 'उत्तर')):
            html_content += f"<p class='heading'>{clean_line}</p>"
        else:
            html_content += f"<p>{clean_line}</p>"
            
    html_content += "</body></html>"

    css = CSS(string=css_style)
    html = HTML(string=html_content)
    return html.write_pdf(stylesheets=[css])

# --- MODIFICATION: Standalone function for Mock Paper Generation ---

def generate_mock_paper_with_llm(
    llm: OpenAI,
    exam: str, 
    subject: str, 
    student_class: str,
    language: str = 'English',
    topic: Optional[str] = None, 
    question_count: Optional[int] = 20,
    duration_minutes: Optional[int] = None
) -> str:
    """
    Generates a mock question paper with prompts localized for multiple Indian languages.
    """
    print(f"\n--- Generating {language.upper()} paper for: {subject} ---")
    
    # Calculate question distribution across sections
    sec_a_count = max(1, int(question_count * 0.40))
    sec_b_count = max(1, int(question_count * 0.25))
    sec_c_count = max(1, int(question_count * 0.20))
    sec_d_count = max(1, int(question_count * 0.10))
    sec_e_count = max(1, int(question_count * 0.05))

    prompt = ""
    
    # --- Base specifications common to all prompts ---
    base_specs = (
        f"**Paper Specifications:**\n"
        f"- **Board/Exam:** {exam}\n"
        f"- **Class:** {student_class}\n"
        f"- **Subject:** {subject}\n"
        f"- **Topic:** {topic if topic else 'General Syllabus'}\n"
        f"- **Time Allowed:** {duration_minutes} minutes\n"
    )

    # --- Language-Specific Prompt Generation ---

    if language == 'Hindi':
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in Hindi.\n\n"
            f"{base_specs}"
            f"- **Language:** Hindi (The entire paper, including all questions, options, and section titles, MUST be in Devanagari script).\n\n"
            f"**Paper Structure Blueprint (in Hindi):**\n"
            f"The paper must be divided into five sections (खंड).\n\n"
            f"1.  **खंड 'अ' (Section A):** Contains **{sec_a_count} बहुविकल्पीय प्रश्न (MCQs)**.\n"
            f"2.  **खंड 'ब' (Section B):** Contains **{sec_b_count} अति लघु उत्तरीय प्रश्न (Very Short Answer Questions)**.\n"
            f"3.  **खंड 'स' (Section C):** Contains **{sec_c_count} लघु उत्तरीय प्रश्न (Short Answer Questions)**.\n"
            f"4.  **खंड 'द' (Section D):** Contains **{sec_d_count} दीर्घ उत्तरीय प्रश्न (Long Answer Questions)**.\n"
            f"5.  **खंड 'इ' (Section E):** Contains **{sec_e_count} केस-आधारित प्रश्न (Case-Based Question)**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'. Options should be labeled क, ख, ग, घ.\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. भारत की राजधानी क्या है?\n"
            f"  [MCQ-OPTIONS] (क) मुंबई | (ख) चेन्नई | (ग) नई दिल्ली | (घ) कोलकाता\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] खंड 'अ').\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the entire paper in Hindi. Begin directly with the paper content."
        )
    elif language == 'Tamil':
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in Tamil.\n\n"
            f"{base_specs}"
            f"- **Language:** Tamil (The entire paper, including all questions, options, and section titles, MUST be in Tamil script).\n\n"
            f"**Paper Structure Blueprint (in Tamil):**\n"
            f"The paper must be divided into five sections (பிரிவு).\n\n"
            f"1.  **பிரிவு 'அ':** Contains **{sec_a_count} கொள்குறி வகை வினாக்கள் (MCQs)**.\n"
            f"2.  **பிரிவு 'ஆ':** Contains **{sec_b_count} மிகக் குறுகிய விடைத் தரும் வினாக்கள் (Very Short Answer Questions)**.\n"
            f"3.  **பிரிவு 'இ':** Contains **{sec_c_count} குறுகிய விடைத் தரும் வினாக்கள் (Short Answer Questions)**.\n"
            f"4.  **பிரிவு 'ஈ':** Contains **{sec_d_count} விரிவான விடைத் தரும் வினாக்கள் (Long Answer Questions)**.\n"
            f"5.  **பிரிவு 'உ':** Contains **{sec_e_count} நிகழ்வு அடிப்படையிலான கேள்வி (Case-Based Question)**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'. Options should be labeled (அ), (ஆ), (இ), (ஈ).\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. இந்தியாவின் தலைநகரம் எது?\n"
            f"  [MCQ-OPTIONS] (அ) மும்பை | (ஆ) சென்னை | (இ) புது தில்லி | (ஈ) கொல்கத்தா\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] பிரிவு 'அ').\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the entire paper in Tamil. Begin directly with the paper content."
        )
    elif language == 'Telugu':
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in Telugu.\n\n"
            f"{base_specs}"
            f"- **Language:** Telugu (The entire paper, including all questions, options, and section titles, MUST be in Telugu script).\n\n"
            f"**Paper Structure Blueprint (in Telugu):**\n"
            f"The paper must be divided into five sections (విభాగం).\n\n"
            f"1.  **విభాగం 'ఎ':** Contains **{sec_a_count} బహుళైచ్ఛిక ప్రశ్నలు (MCQs)**.\n"
            f"2.  **విభాగం 'బి':** Contains **{sec_b_count} అతి స్వల్ప సమాధాన ప్రశ్నలు (Very Short Answer Questions)**.\n"
            f"3.  **విభాగం 'సి':** Contains **{sec_c_count} స్వల్ప సమాధాన ప్రశ్నలు (Short Answer Questions)**.\n"
            f"4.  **విభాగం 'డి':** Contains **{sec_d_count} వ్యాసరూప సమాధాన ప్రశ్నలు (Long Answer Questions)**.\n"
            f"5.  **విభాగం 'ఇ':** Contains **{sec_e_count} కేస్-ఆధారిత ప్రశ్న (Case-Based Question)**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'. Options should be labeled (ఎ), (బి), (సి), (డి).\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. భారతదేశ రాజధాని ఏది?\n"
            f"  [MCQ-OPTIONS] (ఎ) ముంబై | (బి) చెన్నై | (సి) కొత్త ఢిల్లీ | (డి) కోల్‌కతా\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] విభాగం 'ఎ').\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the entire paper in Telugu. Begin directly with the paper content."
        )
    elif language == 'Kannada':
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in Kannada.\n\n"
            f"{base_specs}"
            f"- **Language:** Kannada (The entire paper, including all questions, options, and section titles, MUST be in Kannada script).\n\n"
            f"**Paper Structure Blueprint (in Kannada):**\n"
            f"The paper must be divided into five sections (ವಿಭಾಗ).\n\n"
            f"1.  **ವಿಭಾಗ 'ಎ':** Contains **{sec_a_count} ಬಹು ಆಯ್ಕೆ ಪ್ರಶ್ನೆಗಳು (MCQs)**.\n"
            f"2.  **ವಿಭಾಗ 'ಬಿ':** Contains **{sec_b_count} ಅತಿ ಸಣ್ಣ ಉತ್ತರದ ಪ್ರಶ್ನೆಗಳು (Very Short Answer Questions)**.\n"
            f"3.  **ವಿಭಾಗ 'ಸಿ':** Contains **{sec_c_count} ಸಣ್ಣ ಉತ್ತರದ ಪ್ರಶ್ನೆಗಳು (Short Answer Questions)**.\n"
            f"4.  **ವಿಭಾಗ 'ಡಿ':** Contains **{sec_d_count} ದೀರ್ಘ ಉತ್ತರದ ಪ್ರಶ್ನೆಗಳು (Long Answer Questions)**.\n"
            f"5.  **ವಿಭಾಗ 'ಇ':** Contains **{sec_e_count} ಪ್ರಕರಣ-ಆಧಾರಿತ ಪ್ರಶ್ನೆ (Case-Based Question)**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'. Options should be labeled (ಎ), (ಬಿ), (ಸಿ), (ಡಿ).\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. ಭಾರತದ ರಾಜಧಾನಿ ಯಾವುದು?\n"
            f"  [MCQ-OPTIONS] (ಎ) ಮುಂಬೈ | (ಬಿ) ಚೆನ್ನೈ | (ಸಿ) ಹೊಸ ದೆಹಲಿ | (ಡಿ) ಕೊಲ್ಕತ್ತಾ\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] ವಿಭಾಗ 'ಎ').\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the entire paper in Kannada. Begin directly with the paper content."
        )
    elif language == 'Malayalam':
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in Malayalam.\n\n"
            f"{base_specs}"
            f"- **Language:** Malayalam (The entire paper, including all questions, options, and section titles, MUST be in Malayalam script).\n\n"
            f"**Paper Structure Blueprint (in Malayalam):**\n"
            f"The paper must be divided into five sections (വിഭാഗം).\n\n"
            f"1.  **വിഭാഗം 'എ':** Contains **{sec_a_count} മൾട്ടിപ്പിൾ ചോയിസ് ചോദ്യങ്ങൾ (MCQs)**.\n"
            f"2.  **വിഭാഗം 'ബി':** Contains **{sec_b_count} വളരെ ചെറിയ ഉത്തരം ആവശ്യമായ ചോദ്യങ്ങൾ (Very Short Answer Questions)**.\n"
            f"3.  **വിഭാഗം 'സി':** Contains **{sec_c_count} ചെറിയ ഉത്തരം ആവശ്യമായ ചോദ്യങ്ങൾ (Short Answer Questions)**.\n"
            f"4.  **വിഭാഗം 'ഡി':** Contains **{sec_d_count} ദീർഘമായ ഉത്തരം ആവശ്യമായ ചോദ്യങ്ങൾ (Long Answer Questions)**.\n"
            f"5.  **വിഭാഗം 'ഇ':** Contains **{sec_e_count} കേസ്-അടിസ്ഥാനമാക്കിയുള്ള ചോദ്യം (Case-Based Question)**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'. Options should be labeled (എ), (ബി), (സി), (ഡി).\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. ഇന്ത്യയുടെ തലസ്ഥാനം ഏതാണ്?\n"
            f"  [MCQ-OPTIONS] (എ) മുംബൈ | (ബി) ചെന്നൈ | (സി) ന്യൂ ഡൽഹി | (ഡി) കൊൽക്കത്ത\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] വിഭാഗം 'എ').\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the entire paper in Malayalam. Begin directly with the paper content."
        )
    elif language == 'Sanskrit':
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in Sanskrit.\n\n"
            f"{base_specs}"
            f"- **Language:** Sanskrit (The entire paper, including all questions, options, and section titles, MUST be in Devanagari script).\n\n"
            f"**Paper Structure Blueprint (in Sanskrit):**\n"
            f"The paper must be divided into five sections (खण्डः).\n\n"
            f"1.  **खण्डः 'अ':** Contains **{sec_a_count} बहुविकल्पीयप्रश्नाः (MCQs)**.\n"
            f"2.  **खण्डः 'ब':** Contains **{sec_b_count} अतिलघूत्तरात्मकप्रश्नाः (Very Short Answer Questions)**.\n"
            f"3.  **खण्डः 'स':** Contains **{sec_c_count} लघूत्तरात्मकप्रश्नाः (Short Answer Questions)**.\n"
            f"4.  **खण्डः 'द':** Contains **{sec_d_count} दीर्घोत्तरात्मकप्रश्नाः (Long Answer Questions)**.\n"
            f"5.  **खण्डः 'इ':** Contains **{sec_e_count} प्रकरण-आधारितः प्रश्नः (Case-Based Question)**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'. Options should be labeled क, ख, ग, घ.\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. भारतस्य राजधानी का अस्ति?\n"
            f"  [MCQ-OPTIONS] (क) मुम्बई | (ख) चेन्नई | (ग) नवदिल्ली | (घ) कोलकाता\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] खण्डः 'अ').\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the entire paper in Sanskrit. Begin directly with the paper content."
        )
    else:  # Default to English
        prompt = (
            f"You are an expert educator in India. Your task is to create a high-quality mock question paper in English.\n\n"
            f"{base_specs}"
            f"- **Language:** English\n\n"
            f"**Paper Structure Blueprint:**\n"
            f"The paper must be divided into five sections (A, B, C, D, E).\n\n"
            f"1.  **Section A:** Contains **{sec_a_count} Multiple Choice Questions (MCQs)**.\n"
            f"2.  **Section B:** Contains **{sec_b_count} Very Short Answer Questions**.\n"
            f"3.  **Section C:** Contains **{sec_c_count} Short Answer Questions**.\n"
            f"4.  **Section D:** Contains **{sec_d_count} Long Answer Questions**.\n"
            f"5.  **Section E:** Contains **{sec_e_count} Case-Based Question**.\n\n"
            f"**IMPORTANT FORMATTING RULES:**\n"
            f"- Use '[MCQ-QUESTION]' for the question text.\n"
            f"- Use '[MCQ-OPTIONS]' for options, separated by '|'.\n"
            f"- EXAMPLE:\n"
            f"  [MCQ-QUESTION] 1. What is the capital of France?\n"
            f"  [MCQ-OPTIONS] (A) Berlin | (B) Madrid | (C) Paris | (D) Rome\n"
            f"- Use '[SECTION]' for section titles (e.g., [SECTION] Section A).\n"
            f"- Use '[INSTRUCTION]' for instructions.\n"
            f"Generate the paper according to this precise blueprint. Begin directly with the paper content."
        )
    
    response = llm.complete(prompt)
    return str(response)


def generate_answer_key_with_llm(
    llm: OpenAI, 
    paper_text: str, 
    exam: str, 
    subject: str, 
    student_class: str,
    language: str = 'English'
) -> str:
    """
    Generates a detailed answer key in the specified language by providing
    explicit, localized instructions to the LLM.
    """
    print(f"\n--- Generating {language.upper()} answer key for: {subject} ---")

    # Create a specific language instruction for the LLM prompt.
    if language == 'Hindi':
        lang_instruction = "in Hindi (using Devanagari script)"
    elif language == 'Tamil':
        lang_instruction = "in Tamil (using Tamil script)"
    elif language == 'Telugu':
        lang_instruction = "in Telugu (using Telugu script)"
    elif language == 'Kannada':
        lang_instruction = "in Kannada (using Kannada script)"
    elif language == 'Malayalam':
        lang_instruction = "in Malayalam (using Malayalam script)"
    elif language == 'Sanskrit':
        lang_instruction = "in Sanskrit (using Devanagari script)"
    else: # Default to English
        lang_instruction = "in English"

    prompt = (
        f"You are an expert subject matter teacher for {subject} in India for Class {student_class} under the {exam} board.\n"
        f"You have been given the following question paper, which is written in {language}. "
        f"Your task is to create a detailed and accurate answer key for it {lang_instruction}.\n\n"
        f"**Instructions for the Answer Key:**\n"
        f"1.  For Multiple Choice Questions, provide the correct option and the full answer.\n"
        f"2.  For all other question types, provide a clear, step-by-step model answer.\n"
        f"3.  Maintain the same section and question numbering as the original paper.\n\n"
        f"**CRITICAL RULE:** The entire answer key MUST be generated in {language}. Do not mix languages.\n"
        f"**CRITICAL FORMATTING RULE:** Generate the entire answer key in plain text. Do NOT use Markdown formatting like '#' or '*'.\n\n"
        f"--- START OF QUESTION PAPER ---\n"
        f"{paper_text}\n"
        f"--- END OF QUESTION PAPER ---\n\n"
        f"Now, please generate the complete answer key in {language}."
    )
    
    response = llm.complete(prompt)
    return str(response)

# --- START: NEW ADAPTIVE QUIZ ENGINE FUNCTIONS ---


def generate_interactive_test_with_llm(
    llm: OpenAI,
    subject: str,
    student_class: str,
    question_count: int,
    focus_topics: Optional[list] = None,
    difficulty_mix: Optional[dict] = None
) -> list:
    """
    Generates a structured test in JSON format with rich metadata.
    NOW STRICTLY CONSTRAINED TO MCQs ONLY.
    """
    print("\n--- NEW FUNCTION CALL [MCQ-ONLY INTERACTIVE TEST GENERATOR] ---")

    prompt = (
        f"You are an expert educator creating a quiz for a Class {student_class} student studying {subject}. "
        f"Your task is to generate {question_count} questions in a strict JSON format.\n"
    )

    if focus_topics:
        prompt += f"The test MUST primarily focus on these topics: {', '.join(focus_topics)}.\n"
    
    if difficulty_mix:
        prompt += f"The difficulty mix should be: {str(difficulty_mix)}.\n"

    prompt += (
        "For each question, you must:\n"
        "1.  Identify a specific, granular topic from the syllabus (e.g., 'Trigonometric Ratios', not just 'Trigonometry').\n"
        "2.  Assign a difficulty level: 'Easy', 'Medium', or 'Hard'.\n"
        "3.  Provide the correct answer and three plausible but incorrect 'distractors'. These distractors should represent common student mistakes.\n\n"
        # --- NEW, CRITICAL INSTRUCTION ---
        "**CRITICAL REQUIREMENT: All questions generated MUST be of the 'MCQ' type.**\n"
        # ---
        "**Output MUST be a valid JSON array (`[]`) of objects (`{}`). Do not include any text outside the JSON.**\n"
        "Example format for a single MCQ object:\n"
        "{\n"
        "  \"question_text\": \"What is the value of sin(30°)?\",\n"
        "  \"question_type\": \"MCQ\",\n"
        "  \"topic\": \"Trigonometric Ratios\",\n"
        "  \"difficulty\": \"Easy\",\n"
        "  \"answer\": \"1/2\",\n"
        "  \"distractors\": [\"√3/2\", \"1\", \"0\"]\n"
        "}\n"
    )

    response_str = str(llm.complete(prompt))
    
    try:
        json_match = re.search(r'\[.*\]', response_str, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            return json.loads(response_str)
    except json.JSONDecodeError:
        print(f"Error: LLM did not return valid JSON. Response: {response_str}")
        return []

def get_weakest_topics(profile: dict, subject: str, count: int = 3) -> list:
    """Identifies the topics with the lowest accuracy for a given subject."""
    if subject not in profile or not profile[subject]:
        return []
    
    for topic_data in profile[subject].values():
        if topic_data['total'] > 0:
            topic_data['accuracy'] = topic_data['correct'] / topic_data['total']
        else:
            topic_data['accuracy'] = 0.0

    sorted_topics = sorted(profile[subject].items(), key=lambda item: item[1]['accuracy'])
    return [topic[0] for topic in sorted_topics if topic[1]['total'] > 0][:count]

def generate_personalized_test(llm, subject, student_class, profile):
    """
    Analyzes the user's profile and generates a personalized test.
    """
    weak_topics = get_weakest_topics(profile, subject)
    
    if not weak_topics:
        st.info("No performance data yet. Generating a general test.")
        return generate_interactive_test_with_llm(
            llm=llm, subject=subject, student_class=student_class, question_count=3
        )

    st.info(f"Detected weak areas: {', '.join(weak_topics)}. Generating a focused practice test...")
    return generate_interactive_test_with_llm(
        llm=llm,
        subject=subject,
        student_class=student_class,
        question_count=3,
        focus_topics=weak_topics,
        difficulty_mix={'Easy': 2, 'Medium': 1}
    )

# --- END: NEW ADAPTIVE QUIZ ENGINE FUNCTIONS ---

@st.cache_resource
def initialize_system(_llm: OpenAI):
    """Initialize the RAG system by loading the persisted hierarchical index."""
    try:
        # llm = OpenAI(model="gpt-4.1-nano", api_key=api_key)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large", api_key=api_key)

        logger.info("Connecting to local Qdrant instance...")
        client = qdrant_client.QdrantClient(path=QDRANT_PATH)
        
        vector_store = QdrantVectorStore(client=client, collection_name=QDRANT_COLLECTION_NAME)

        logger.info("Loading storage context from disk...")
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
            persist_dir="./storage"
        )

        logger.info("Loading index from storage...")
        index = load_index_from_storage(storage_context)
        logger.info("Index loaded successfully.")

        # --- Initialize the reranker model ONCE, at startup ---
        logger.info("Initializing SentenceTransformerRerank model...")
        reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=3)
        logger.info("Reranker model loaded successfully.")
        
        VERBATIM_TEMPLATE_STR = """
        The following is the exact text from a document.
        You must output this text VERBATIM. Do not add any introduction, conclusion, summary, or any other words.
        Just return the raw text exactly as it appears.

        ---
        {context_str}
        ---
        """
        VERBATIM_TEMPLATE = PromptTemplate(VERBATIM_TEMPLATE_STR)

        def query_question_papers(
            query: str, 
            subject: Optional[str] = None,
            code: Optional[str] = None,
            exam: Optional[str] = None,
            year: Optional[int] = None,
            shift: Optional[str] = None
        ) -> str:
            print("\n--- TOOL CALLED [VERBATIM MODE] ---")
            print(f"Query: '{query}', Subject: '{subject}', Code: '{code}', "
                  f"Exam: '{exam}', Year: '{year}', Shift: '{shift}'")

            
            final_filters = None
            base_filter_list = [] # We'll build our list of conditions here

            # --- Main Filtering Logic Starts Here ---

            # CASE 1: The user is asking for a JEE paper.
            if exam and "jee" in exam.lower():
                print("INFO: Detected JEE query. Building filters for exam and year.")
                base_filter_list.append(ExactMatchFilter(key="exam", value="JEE Main"))
                if year:
                    base_filter_list.append(ExactMatchFilter(key="year", value=year))
                final_filters = MetadataFilters(filters=base_filter_list)

            # CASE 2: The user is asking for a CBSE paper.
            else:
                print("INFO: Detected CBSE query. Building subject-specific filters.")
                base_filter_list.append(ExactMatchFilter(key="type", value="cbse"))
                if year:
                    base_filter_list.append(ExactMatchFilter(key="year", value=year))
                
                # Now, handle the different subject types for CBSE
                if subject:
                    s_lower = subject.lower()
                    
                    # Sub-Case 2a: Mathematics (requires an OR condition)
                    if "mathematic" in s_lower:
                        print("INFO: Handling 'Mathematics'. Creating OR filter.")
                        math_or_filter = MetadataFilters(
                            filters=[
                                ExactMatchFilter(key="subject", value="Mathematics Basic"),
                                ExactMatchFilter(key="subject", value="Mathematics Standard")
                            ],
                            condition="or"
                        )
                        # Add the special OR filter object to our main list of conditions
                        base_filter_list.append(math_or_filter)
                        # The final filter will require ALL of these conditions to be met
                        final_filters = MetadataFilters(filters=base_filter_list, condition="and")

                    # Sub-Case 2b & 2c: All other subjects (Languages, Science, etc.)
                    else:
                        print(f"INFO: Handling standard subject '{subject}'. Using exact match.")
                        base_filter_list.append(ExactMatchFilter(key="subject", value=subject))
                        final_filters = MetadataFilters(filters=base_filter_list)
                else:
                    # If no subject is provided, just use the base filters
                    final_filters = MetadataFilters(filters=base_filter_list)

            # --- Filtering Logic Ends ---

            print(f"DEBUG: Final filters being passed to retriever: {final_filters}")

            filtered_base_retriever = index.as_retriever(
                similarity_top_k=12,
                # THIS IS THE CRITICAL FIX: We now pass the final_filters object
                filters=final_filters 
            )
            
            merging_retriever = AutoMergingRetriever(
                filtered_base_retriever, index.storage_context, verbose=True
            )
            
            # reranker = SentenceTransformerRerank(model="BAAI/bge-reranker-base", top_n=3)

            custom_synthesizer = get_response_synthesizer(
                response_mode="compact",
                text_qa_template=VERBATIM_TEMPLATE,
            )

            query_engine = RetrieverQueryEngine.from_args(
                retriever=merging_retriever,
                node_postprocessors=[reranker],
                response_synthesizer=custom_synthesizer,
            )
            
            response = query_engine.query(query)
            print("Response generated using verbatim prompt.")
            return str(response)

        rag_tool = FunctionTool.from_defaults(
            fn=query_question_papers,
            name="previous_year_question_engine",
            description=(
                "Use this tool ONLY to retrieve specific questions or entire papers from previous year exams when the user "
        "explicitly asks for 'previous year questions', 'past papers', etc. "
        "CRITICAL: You MUST use the full conversation history to gather context. "
        
        "1. **Construct a detailed 'query' string.** The query MUST include the subject, class, and board. "
        "   Example: If the user is in 'CBSE class 10' and asks for 'maths past questions', the query MUST be "
        "   'important previous year questions for CBSE class 10 Mathematics'. "
        
        "2. **Provide all available filters using ONLY the following exact values:** "
        "   - For the 'exam' filter, the ONLY valid options are 'JEE Main'. Do NOT include the class number (e.g., '10' or '12') in the exam name. "
        "   - For the 'subject' filter, use standard names like 'Mathematics', 'Science', etc. "
        "   - For the 'year' filter, use a four-digit integer like 2023. "
        
        "Correct Example Tool Call: previous_year_question_engine(query='...', subject='Mathematics', exam='none', year=2023) "
        "Incorrect Example Tool Call: previous_year_question_engine(query='...', exam='CBSE Class 10') "
        
        "Do NOT use this tool for general definitions or explanations."
            )
        )

        openai_client = OpenAI_Client(api_key=api_key)

        def generate_image_from_prompt(prompt: str) -> str:
            """
            Generates an image based on a textual prompt using DALL-E 3 and returns the image URL.
            The prompt should be a detailed description of the desired image.
            """
            print(f"\n--- TOOL CALLED [IMAGE GENERATOR] ---")
            print(f"Prompt: '{prompt}'")
            try:
                response = openai_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    response_format="url"
                )
                image_url = response.data[0].url
                return f"IMAGE_URL::{image_url}"
            except Exception as e:
                return f"Error generating image: {str(e)}"

        # image_generation_tool = FunctionTool.from_defaults(
        #     fn=generate_image_from_prompt,
        #     name="image_generator",
        #     description=(
        #         "Use this tool to generate ncert text book style very simple image, unlabeled diagram, or visual aid for a school student. "
        #         "The prompt sent to this tool MUST be detailed and specify the style (e.g., 'simple diagram for a child'), "
        #         "context (e.g., 'for a 10th grade student'), and labeling requirements (e.g., 'unlabeled')."
        #     )
        # )


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
                cse_id = os.getenv("GOOGLE_CSE_ID")
                if not api_key or not cse_id:
                    return "Error: Google API credentials are not configured."

                # --- MODIFICATION FOR VARIETY ---
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
                    return f"IMAGE_URL::{image_url}"
                else:
                    # Fallback: If we're past the first result and find nothing, try the first result again.
                    if start_index > 1:
                        print(f"Fallback: No result at index {start_index}. Trying the top result.")
                        res_fallback = service.cse().list(q=query, cx=cse_id, searchType='image', num=1, start=1, safe='high').execute()
                        if 'items' in res_fallback and len(res_fallback['items']) > 0:
                            return f"IMAGE_URL::{res_fallback['items'][0]['link']}"
                    return "Could not find a suitable image for that query."

            except Exception as e:
                logger.error(f"Google Image Search Error: {e}", exc_info=True)
                return f"Error searching for image: {str(e)}"
            
            # This creates the tool object that the agent can use.
        image_retrieval_tool = FunctionTool.from_defaults(
            fn=search_web_for_image,
            name="image_search",
            description=(
                "Use this tool to search the web for a diagram, photo, maps or image. "
                "Use this for requests like 'draw a diagram of...', 'map pointing of....', 'outlined map of...', 'labelled diagram of...','flowchart on...', 'show me a picture of...','find an image of...'. etc."
            )
        )

        # --- NEW TOOL FUNCTION DEFINITION ---
        def initiate_adaptive_quiz(subject: str, topic: str) -> str:
            """
            Initiates a short, adaptive quiz for the user on a specific topic.
            This tool should be called by the agent after getting the user's consent.
            """
            print(f"\n--- TOOL CALLED [ADAPTIVE QUIZ GENERATOR] for Subject: {subject}, Topic: {topic} ---")
            
             # 1. The conversational topic is now the highest priority "seed" for the quiz.
            seed_topic = topic

            # 2. Check the profile for other weak topics to potentially mix in.
            weak_topics_from_profile = get_weakest_topics(
            profile=st.session_state.performance_profile, 
            subject=subject, 
            count=2
            )

            # 3. Build the final list of topics. The seed topic is ALWAYS included.
            #    This ensures the quiz is anchored to the current lesson.
            focus_topics = [seed_topic]
            for t in weak_topics_from_profile:
                # Add other weak topics only if they are different from the seed topic
                # and we still have room in our small quiz.
                if t.lower() != seed_topic.lower() and len(focus_topics) < 3:
                    focus_topics.append(t)
    
            # Let the user know what the quiz will cover.
            st.info(f"Generating a quiz focused on: {', '.join(focus_topics)}")

            # 4. Directly call the question generator with our carefully selected topics.
            #    This gives the LLM a much tighter constraint.
            quiz_questions = generate_interactive_test_with_llm(
                llm=llm_instance,
                subject=subject,
                student_class="10", # TODO: Make this dynamic from the user's initial setup.
                question_count=3,
                focus_topics=focus_topics,
                difficulty_mix={'Easy': 1, 'Medium': 2} # A good mix for a learning quiz
            )

            if not quiz_questions:
                return "I'm sorry, I had a little trouble creating a quiz on that specific topic right now. Let's continue our lesson."

            # 5. Set up the quiz state (this part remains the same).
            st.session_state.current_test = quiz_questions
            st.session_state.current_question_index = 0
            st.session_state.conversation_mode = "quiz"
    
            return "Quiz created successfully. The interactive flashcard will now appear."
           

        # --- CREATE THE FUNCTIONTOOL ---
        adaptive_quiz_tool = FunctionTool.from_defaults(
            fn=initiate_adaptive_quiz,
            name="initiate_adaptive_quiz",
            description=(
                "Use this to start a short, adaptive quiz for the user on a given subject and topic. "
                "Only call this after the user agrees to take a quiz."
            )
        )
        
        # # --- UPDATE THE AGENT'S TOOL LIST ---
        # agent = OpenAIAgent.from_tools(
        #     [rag_tool, image_generation_tool, adaptive_quiz_tool], # <-- ADD THE NEW TOOLS HERE
        #     llm=_llm,
        #     system_prompt=SYSTEM_PROMPT,
        #     verbose=True
        # )
        # return agent
    
        # --- Change it to this (removed image_generation_tool) ---
        agent = OpenAIAgent.from_tools(
            [rag_tool, image_retrieval_tool, adaptive_quiz_tool],
            llm=_llm,
            system_prompt=SYSTEM_PROMPT,
            verbose=True
        )
        return agent
     
    except Exception as e:
        st.error(f"Failed to initialize the system: {str(e)}")
        logger.error(f"Initialization error: {str(e)}", exc_info=True)
        st.stop()
        
# --- Streamlit UI ---

# --- Session state Initialization ---
# This block runs ONCE per session and sets up the app's memory.
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Namaste! To help you better, please tell me which board you are from, which class (5-12), and which subject you need help with."}]
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = ""
if 'answer_key_pdf_data' not in st.session_state:
    st.session_state.answer_key_pdf_data = None
if 'answer_key_pdf_filename' not in st.session_state:
    st.session_state.answer_key_pdf_filename = ""
if 'performance_profile' not in st.session_state:
    st.session_state.performance_profile = {}
if 'current_test' not in st.session_state:
    st.session_state.current_test = None
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'conversation_mode' not in st.session_state:
    st.session_state.conversation_mode = "tutoring"
if 'user_choice' not in st.session_state:
    st.session_state.user_choice = None
if 'image_search_history' not in st.session_state:
    st.session_state.image_search_history = {}


# --- INITIAL SETUP (RUNS ONCE AT THE TOP) ---
st.title("AI Tutor Bot")

# Load user profile and initialize core components
user_profile = profile_manager.load_profile()
llm_instance = OpenAI(model="gpt-4.1-mini", api_key=api_key) # Using a stronger model like gpt-4-turbo is recommended for the analysis task
agent = initialize_system(llm_instance)


# --- SIDEBAR SETUP ---
with st.sidebar:
    st.header("Settings & Tools")

    with st.expander("🎯 Set Your Goal", expanded=True):
        exam_date_input = st.date_input(
            "Select Your Final Exam Date",
            value=datetime.fromisoformat(user_profile['exam_date']) if user_profile.get('exam_date') else None
        )
        target_score = st.slider(
            "Select Your Target Score (%)",
            min_value=40, max_value=100,
            value=user_profile.get('target_score', 85)
        )
        if st.button("Save Goals"):
            user_profile['exam_date'] = exam_date_input.isoformat() if exam_date_input else None
            user_profile['target_score'] = target_score
            profile_manager.save_profile(user_profile)
            st.success("Goals saved!")
            st.rerun()

    with st.expander("📄 Mock Paper Generator"):
        # Use a form to group inputs and the submission button
        with st.form("mock_paper_form"):
            st.write("Select options to create your practice test.")
            language = st.selectbox("Language", list(FONT_MAP.keys()))
            exam_type = st.selectbox("Exam", ["CBSE", "ICSE", "JEE Main"])
            student_class = st.selectbox("Class", ["5", "6", "7", "8", "9", "10", "11", "12"])
            subject = st.text_input("Subject", "Science")
            topic = st.text_input("Topic (Optional)")
            q_count = st.number_input("Number of Questions", min_value=1, max_value=50, value=10, step=1)
            duration = st.number_input("Duration (in minutes)", min_value=10, max_value=180, value=60, step=10)
            
            # The submit button for the form
            submitted = st.form_submit_button("Generate Paper & Answer Key")

            if submitted:
                with st.spinner(f"Generating your {language} mock paper... This may take a moment."):
                    try:
                        paper_text = generate_mock_paper_with_llm(
                            llm=llm_instance, exam=exam_type, subject=subject, student_class=student_class,
                            language=language, topic=topic, question_count=q_count, duration_minutes=duration
                        )
                        
                        pdf_title = f"{exam_type} Mock Paper - Class {student_class} {subject}"
                        pdf_bytes = create_structured_pdf(paper_text, pdf_title, language=language)
                        st.session_state.pdf_data = pdf_bytes
                        st.session_state.pdf_filename = f"{exam_type}_{subject}_Class{student_class}_{language}_Mock_Paper.pdf"
                        
                        st.info("Question paper generated. Now creating the answer key...")

                        answer_key_text = generate_answer_key_with_llm(
                            llm=llm_instance, paper_text=paper_text, exam=exam_type, subject=subject,
                            student_class=student_class, language=language
                        )
                        
                        answer_key_text = str(answer_key_text).replace('**', '').replace('*', '').replace('#', '')
                        answer_key_title = f"Answer Key for {pdf_title}"
                        answer_key_pdf_bytes = create_answer_key_pdf(answer_key_text, answer_key_title, language=language)
                        st.session_state.answer_key_pdf_data = answer_key_pdf_bytes
                        st.session_state.answer_key_pdf_filename = f"{exam_type}_{subject}_Class{student_class}_{language}_Answer_Key.pdf"

                        st.success("Success! Your mock paper and answer key are ready.")
                    
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        logger.error(f"Mock paper generation failed: {e}", exc_info=True)
                        st.session_state.pdf_data = None
                        st.session_state.answer_key_pdf_data = None

    # Display download buttons in the sidebar, but outside the form/expander
    if st.session_state.get('pdf_data'):
        st.download_button(
            label="Download Question Paper (PDF)", data=st.session_state.pdf_data,
            file_name=st.session_state.pdf_filename, mime="application/pdf"
        )
    if st.session_state.get('answer_key_pdf_data'):
        st.download_button(
            label="Download Answer Key (PDF)", data=st.session_state.answer_key_pdf_data,
            file_name=st.session_state.answer_key_pdf_filename, mime="application/pdf", type="primary"
        )

# --- MAIN UI TABS ---
tab1, tab2 = st.tabs(["💬 Tutor Chat", "📊 Analytics Dashboard"])

# --- TUTOR CHAT TAB ---

with tab1:
    st.write("Ask me anything about your syllabus or practice with previous year's questions!")

    if st.button("Clear Conversation History"):
        st.session_state.messages = [{"role": "assistant", "content": "History cleared! How can I help you now?"}]
        st.session_state.conversation_mode = "tutoring"
        st.session_state.current_test = None
        st.session_state.user_choice = None
        st.session_state.current_question_index = 0
        agent.reset()
        st.rerun()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], str) and message["content"].startswith("IMAGE_URL::"):
                image_url = message["content"].split("::")[1]
                st.image(image_url)
            else:
                st.markdown(message["content"])

    
    if user_input := st.chat_input("Your question or query:", disabled=(st.session_state.conversation_mode != "tutoring")):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if st.session_state.conversation_mode == "tutoring":
            try:
                response_content = None
                image_url = None
                
                with st.spinner("Thinking..."):
                    logger.info("--- Calling Agent  ---")
                    # Always call the agent directly with the raw user input
                    response = agent.chat(user_input) 
                    full_response_str = str(response)

                    # Parse the response for text and image
                    image_match = re.search(r"IMAGE_URL::(https?://[^\s]+)", full_response_str)
                    if image_match:
                        image_url = image_match.group(1)
                        response_content = full_response_str.split("IMAGE_URL::")[0].strip()
                    else:
                        response_content = full_response_str
                
                # Process and display the final response
                if response_content:
                    st.session_state.messages.append({"role": "assistant", "content": response_content})
                
                if image_url:
                    st.session_state.messages.append({"role": "assistant", "content": f"IMAGE_URL::{image_url}"})

                st.rerun()

            except Exception as e:
                error_message = f"Sorry, an error occurred: {str(e)}"
                st.error(error_message)
                logger.error(f"Query processing error: {str(e)}", exc_info=True)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

    # --- INTERACTIVE QUIZ & COMPLETION LOGIC (Part of the Chat flow) ---
    if st.session_state.conversation_mode == "quiz" and st.session_state.current_test:
        idx = st.session_state.current_question_index
        if idx >= len(st.session_state.current_test):
            st.session_state.conversation_mode = "quiz_complete"
            st.rerun()

        question = st.session_state.current_test[idx]
        with st.container(border=True):
            st.subheader(f"Quiz Time! Question {idx + 1}/{len(st.session_state.current_test)}")
            st.write(f"**Topic:** {question['topic']} | **Difficulty:** {question['difficulty']}")
            st.markdown(f"### {question['question_text']}")
            
            options = question['distractors'] + [question['answer']]
            if f"options_{idx}" not in st.session_state:
                random.shuffle(options)
                st.session_state[f"options_{idx}"] = options
            
            user_choice = st.radio("Select your answer:", st.session_state[f"options_{idx}"], key=f"quiz_{idx}", index=None)

            if st.button("Lock-in Answer", key=f"submit_{idx}"):
                if user_choice is None:
                    st.warning("Please select an answer!")
                else:
                    is_correct = (user_choice == question['answer'])
                    # --- LOG THE QUIZ RESULT ---
                    user_profile = profile_manager.log_quiz_result(
                        profile=user_profile, topic=question['topic'], is_correct=is_correct
                    )
                    
                    if is_correct:
                        st.success("Correct! Great job! ✅")
                    else:
                        st.error(f"Not quite. The correct answer was: **{question['answer']}** ❌")
                    
                    time.sleep(2)
                    st.session_state.current_question_index += 1
                    st.rerun()

    elif st.session_state.conversation_mode == "quiz_complete":
        st.balloons()
        st.success("Quiz complete! Your performance profile has been updated.")
        st.info("We can now continue our lesson. Click the button below to return to the chat.")

        if st.button("Continue Learning"):
            test_len = len(st.session_state.current_test) if st.session_state.current_test else 0
            st.session_state.conversation_mode = "tutoring"
            st.session_state.current_test = None
            st.session_state.current_question_index = 0
            for i in range(test_len):
                if f"options_{i}" in st.session_state: del st.session_state[f"options_{i}"]
            st.rerun()


# --- ANALYTICS DASHBOARD TAB ---
with tab2:
    st.header("Your Performance Dashboard")
    
    # You would get the subject from st.session_state after the user confirms it in the chat
    # For now, we'll use a placeholder or the last one from the mock paper generator
    current_subject = "Science" 

    if not user_profile['performance_log']:
        st.info("Your dashboard is empty. Complete a quiz in the 'Tutor Chat' tab to see your progress!")
    else:
        metrics = analytics.calculate_metrics(user_profile, current_subject)
        
        with st.spinner("🤖 Generating AI-powered forecast..."):
            readiness = analytics.predict_readiness_with_llm(
                metrics, user_profile, current_subject, llm_instance
            )

        # --- Display KPIs, Forecast, and Insights ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Study Streak", f"{metrics['streak_days']} Days 🔥")
        col2.metric("Avg. Accuracy", f"{metrics['average_accuracy']}%")
        col3.metric("Syllabus Covered", f"{metrics['topics_covered_percent']}%")
        col4.metric("Hours Studied", f"{metrics['hours_spent']} hrs")

        st.divider()

        col1, col2 = st.columns([2, 1.5])
        with col1:
            st.subheader("💡 AI Coach Analysis")
            st.markdown("**Key Observations** 👍")
            for item in readiness['key_observations']: st.markdown(f"- {item}")
            st.markdown("**Key Risks** ⚠️")
            for item in readiness['key_risks']: st.markdown(f"- {item}")

        with col2:
            st.subheader("🎯 Exam Readiness Forecast")
            predicted = readiness['predicted_score']
            target = user_profile.get('target_score', 85)
            st.progress(predicted / 100, text=f"Predicted Score: {predicted}%")
            delta = round(predicted - target, 1)
            st.metric(label=f"Against Your Target ({target}%)", value=f"{predicted}%", delta=f"{delta}%")
            st.caption(f"AI Confidence: **{readiness['confidence_level']}**")

        st.divider()

        st.subheader("Actionable Recommendations")
        for item in readiness['recommendations']:
            st.info(f"**Tips\:** {item}")
        
        st.subheader("Performance Breakdown by Topic")
        if metrics.get('performance_by_topic'):
            topic_df = pd.DataFrame(list(metrics['performance_by_topic'].items()), columns=['Topic', 'Accuracy']).sort_values("Accuracy", ascending=False)
            chart = alt.Chart(topic_df).mark_bar().encode(
                x=alt.X('Accuracy:Q', title='Accuracy (%)', scale=alt.Scale(domain=[0, 100])),
                y=alt.Y('Topic:N', sort='-x', title='Topic'), tooltip=['Topic', 'Accuracy']
            ).properties(title='Accuracy by Topic')
            st.altair_chart(chart, use_container_width=True)

