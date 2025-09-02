from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict
import sqlite3
import hashlib
import jwt
import datetime
from pathlib import Path
import json
import openai
import os
import re
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import asyncio

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise Exception("Open AI API key not found")

SYSTEM_PROMPT = """
You are a supportive, patient, and helpful AI tutor for students in India, specializing in classes 9-12 for all boards including state boards (e.g., BSE Telangana, BSE Andhra Pradesh), CBSE, ICSE, and ISC. You cover all subjects such as Social Studies, Mathematics, Science, English, Hindi, and others as per the official syllabi.

## Initial Interaction
- If the user has not specified their board, class (9-12), and subject, greet them warmly: "Welcome! To help you better, please tell me which board you are from (e.g., CBSE, ICSE, ISC, BSE Telangana), which class (9-12), and which subject you need help with."
- Parse the user's response to extract the board, class, and subject. If incomplete, ask for missing details politely.
- Once all details are provided, confirm: "Great! I'll be your AI tutor for [subject] in Class [class] under the [board] board. How can I assist you today?"
- Upon subject selection, dynamically retrieve the complete syllabus details by simulating access to official sources (e.g., SCERT Telangana for BSE Telangana, NCERT for CBSE, CISCE for ICSE/ISC). Use the following internal questioning prompts to guide retrieval:
  - "What are the chapters in the [board] Class [class] [subject] textbook?"
  - "What are the topics and subtopics covered in each chapter, particularly for [specific unit, e.g., Trigonometry]?"
  - "What are the major topics and, for Mathematics, major theorems emphasized in recent [board] Class [class] [subject] exams?"
  - "Which topics are excluded as activity/project work or not emphasized in recent exams for [board] Class [class] [subject]?"
- Retrieve the complete list of chapters, topics, subtopics, major exam-relevant topics, and, for Mathematics, major theorems (e.g., trigonometric identities like sin²θ + cos²θ = 1 for BSE Telangana Class 10 Mathematics, Chapter 11 Trigonometry). List chapters and topics in order, with full titles, ensuring no omissions. Exclude topics marked for activity/project work or less emphasized in recent exams.
- Retain these details for the entire conversation unless the user requests a change (e.g., "switch to another subject").

## Core Rules (Strictly Enforce)
- Answer ONLY questions related to the official syllabus of the specified board’s Class [class] [subject] textbook, focusing on the specific unit where the topic belongs.
- For every concept explanation, dive directly into the explanation without mentioning chapter, syllabus, or subject details (e.g., avoid “The chapter on laws of motion in Class 9 Science...” ) and while giving text definition avoid saying like "In textbook its is defined as or something similar like that". Strictly follow this four-part structure in a seamless, conversational flow without using headings:
  1. Start with a detailed, engaging real-life example that captivates students’ interest and clearly illustrates the concept (e.g., for Newton’s First Law, describe a water slide or amusement park scenario, avoiding brief or generic examples).
  2. Provide the textbook definition or explanation of the concept, using exact terminology and methods from the syllabus, ensuring accuracy and clarity, while giving this definition also add if there are any formulas or anything what should be noted.
  3. Include a detailed additional example, aligned with the textbook’s style, that reinforces the concept through a different scenario (e.g., a textbook problem or a practical situation like moving a suitcase).
  4. End with an understanding check, saying: “Does this make sense, or should I explain it another way?” followed by a short, syllabus-based quiz question to gauge understanding (e.g., “Quick check: What does inertia mean, and why does a heavier object have more of it?”).
- Never deviate from this structure for concept explanations, ensuring examples are detailed, engaging, and spark student curiosity.
- You have no knowledge outside the official syllabi for Indian boards (state, CBSE, ICSE, ISC) for classes 9-12. Do not answer general questions or topics from other classes, boards, units, or non-educational queries.
- If a question is outside the syllabus, unit, or subject, reply: “I’m sorry, but this doesn’t seem to be part of the syllabus for the specified unit. I’m here to help with topics from that syllabus only! Would you like to ask about something from it, or switch to a different board/class/subject?”
- Never invent or assume content. Stick strictly to the textbook content without adding external information or advanced terminology.
- If an explanation deviates from the four-part structure or includes syllabus metadata in the explanation, self-correct by regenerating the response to comply before sending.
- Strictly avoid mentioning the board name, class, or subject within any concept explanation. These may only appear in initial setup or syllabus-confirmation messages.

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
"""

app = FastAPI(title="AI Study Tutor API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = "dsfcgvhbjnkmljbhvgcfgvhbjnk"  # In production, use environment variable
ALGORITHM = "HS256"

# Database setup
DB_PATH = Path("database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'parent')),
            school_name TEXT NOT NULL,
            child_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Study plans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            board TEXT NOT NULL,
            class_num INTEGER NOT NULL,
            plan_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Progress tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id TEXT NOT NULL,
            completed BOOLEAN DEFAULT FALSE,
            score REAL,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Quiz questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            chapter TEXT NOT NULL,
            topic TEXT NOT NULL,
            question_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # User preferences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            board TEXT NOT NULL,
            class_num INTEGER NOT NULL,
            personality_type TEXT DEFAULT 'balanced',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class UserRegister(BaseModel):
    firstName: str
    middleName: Optional[str] = None
    lastName: str
    email: str
    password: str
    role: str
    schoolName: str
    childUsername: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class StudyPlanRequest(BaseModel):
    subject: str
    board: str
    class_num: int
    start_date: str
    end_date: str
    extra_chapters: List[str] = []
    weak_chapters: List[str] = []
    personality_type: str = "balanced"

class UserPreferenceRequest(BaseModel):
    board: str
    class_num: int
    personality_type: str = "balanced"

class StudyPlan(BaseModel):
    subject: str
    board: str
    class_num: int
    plan_data: Dict

class ProgressUpdate(BaseModel):
    task_id: str
    completed: bool
    score: Optional[float] = None

class TaskProgressUpdate(BaseModel):
    subject: str
    week: str
    task_id: int
    completed: bool
    progress: int = 0
    score: Optional[float] = None

class QuizRequest(BaseModel):
    subject: str
    board: str
    class_num: int
    chapters: List[str] = []
    level: str = 'beginner'
    mode: str = ''
    chapter: str = ''
    topic: str = ''
    topics: List[str] = []  # Added to handle chapter quiz topics

class SyllabusRequest(BaseModel):
    board: str
    class_num: int
    subject: str

class ExplanationRequest(BaseModel):
    board: str
    class_num: int
    subject: str
    chapter: str
    topic: str

class ImageRequest(BaseModel):
    subject: str
    topic: str
    subtopic: str = None

class SubtopicsRequest(BaseModel):
    board: str
    class_num: int
    subject: str
    chapter: str
    topic: str

class RescheduleRequest(BaseModel):
    subject: str
    missed_date: str

class ChatRequest(BaseModel):
    board: str
    class_num: int
    subject: str
    chapter: str
    topic: str
    subtopic: str
    message: str

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token or missing authorization header")

def get_user_by_id(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "firstName": user[1],
            "middleName": user[2],
            "lastName": user[3],
            "email": user[4],
            "role": user[6],
            "schoolName": user[7],
            "childUsername": user[8]
        }
    return None

def generate_subjects(board: str, class_num: int) -> List[Dict]:
    prompt = f"""
    List all subjects available for {board} Class {class_num} based on the official syllabus.
    Return a valid JSON array of objects with 'name' field for each subject, e.g., [{{"name": "Mathematics"}}, {{"name": "Science"}}].
    Ensure the response is strictly JSON with no additional text or markdown.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^\s*```json\s*|\s*```$', '', content)
        content = re.sub(r',\s*([\]}])', r'\1', content)
        content = content.strip()
        if not content.startswith('['):
            content = f"[{content}]"
        subjects = json.loads(content)
        return [{"name": s["name"], "board": board, "class_num": class_num} for s in subjects]
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in generate_subjects: {str(e)} - Raw content: {content}")
        raise HTTPException(status_code=500, detail=f"Error parsing subjects data: {str(e)}")
    except Exception as e:
        print(f"Error in generate_subjects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating subjects: {str(e)}")

async def get_syllabus(board: str, class_num: int, subject: str) -> Dict:
    cached = load_cached_syllabus(board, class_num, subject)
    if cached:
        return cached
    prompt = f"""
    Provide the complete syllabus for {board} Class {class_num} {subject} as per the official curriculum (NCERT for CBSE, SCERT Telangana for BSE Telangana, CISCE for ICSE/ISC).
    For CBSE, use NCERT textbooks as the source. For BSE Telangana, use SCERT Telangana textbooks.
    List ALL chapters and their major topics in a structured JSON format with a top-level 'chapters' key. For each chapter, include:
    - Chapter name (as 'name'), exactly matching the official textbook titles
    - List of super important topics (key concepts emphasized in exams, as 'topics')
    - List of subtopics for each topic (as 'subtopics'), if applicable
    Exclude topics marked for activities/projects or less emphasized in recent exams.
    Return only the JSON object, without any Markdown or code block formatting.
    Example:
    {{"chapters": [{{"name": "Chapter Name", "topics": [{{"name": "Topic 1", "subtopics": ["Subtopic 1", "Subtopic 2"]}}, {{"name": "Topic 2", "subtopics": []}}]}}]}}
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=4000
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^\s*```json\s*|\s*```$', '', content)
        content = re.sub(r',\s*([\]}])', r'\1', content)
        content = content.strip()
        syllabus = json.loads(content)
        save_cached_syllabus(board, class_num, subject, syllabus)
        return syllabus
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating syllabus: {str(e)}")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_subtopics(board: str, class_num: int, subject: str, chapter: str, topic: str) -> List[str]:
    prompt = f"""
    {SYSTEM_PROMPT}

    For {board} Class {class_num} {subject}, provide the subtopics for the topic '{topic}' in the chapter '{chapter}' as per the official curriculum (NCERT for CBSE, SCERT Telangana for BSE Telangana, CISCE for ICSE/ISC).
    Return a JSON list of subtopics, e.g., ["Subtopic 1", "Subtopic 2"].
    Exclude subtopics marked for activities/projects or less emphasized in recent exams.
    Return only the JSON list, without any Markdown or code block formatting.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^\s*```json\s*|\s*```$', '', content)
        subtopics = json.loads(content)
        return subtopics if isinstance(subtopics, list) else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching subtopics: {str(e)}")

def generate_nudge(completed_tasks: int, total_tasks: int, missed_tasks: int, weak_areas: List[str]):
    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
    if missed_tasks > 0:
        return f"Oops, looks like you missed {missed_tasks} tasks! No worries, let's focus on {', '.join(weak_areas[:2]) if weak_areas else 'your studies'} and conquer them together!"
    elif weak_areas:
        return f"You're making progress, but let's strengthen your skills in {', '.join(weak_areas[:2])}. Keep pushing, brave scholar!"
    elif completion_rate > 0.8:
        return "You're dominating the knowledge kingdom like a true champion! Keep ruling!"
    elif completion_rate > 0.5:
        return "Great progress, adventurer! You're halfway to mastering this realm. Let's keep exploring!"
    else:
        return "Every step counts, young scholar! Let's dive into the next quest and build your skills!"

def reschedule_plan(user_id: int, subject: str, missed_date: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT plan_data FROM study_plans 
        WHERE user_id = ? AND subject = ?
        ORDER BY created_at DESC LIMIT 1
    """, (user_id, subject))
    plan_result = cursor.fetchone()
    if not plan_result:
        conn.close()
        raise HTTPException(status_code=404, detail="Study plan not found")
    plan = json.loads(plan_result[0])
    
    updated_plan = {}
    missed_tasks = []
    for week, tasks in plan.items():
        updated_plan[week] = []
        for task in tasks:
            if task["date"] == missed_date and not task["completed"]:
                missed_tasks.append(task)
            else:
                updated_plan[week].append(task)
    
    last_week = max(int(w) for w in updated_plan.keys())
    for task in missed_tasks:
        new_week = str(last_week + 1)
        updated_plan[new_week] = updated_plan.get(new_week, [])
        task["date"] = (datetime.strptime(task["date"], "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
        updated_plan[new_week].append(task)
        last_week += 1
    
    cursor.execute("""
        UPDATE study_plans 
        SET plan_data = ?
        WHERE user_id = ? AND subject = ?
    """, (json.dumps(updated_plan), user_id, subject))
    conn.commit()
    conn.close()
    return updated_plan

async def generate_quiz_questions(subject: str, chapter: str, topic: str = '', level: str = 'beginner', quiz_type: str = 'initial', chapters: List[str] = [], topics: List[str] = []):
    if quiz_type == 'initial':
        prompt = f"""
        {SYSTEM_PROMPT}

        Generate exactly 1 quiz question for {subject}, chapter '{chapter}'{f', topic {topic}' if topic else ''} at {level} level.
        The question must include ALL of the following fields:
        - question: A clear, specific question about the chapter content
        - options: An array of exactly 4 multiple-choice options (A, B, C, D)
        - answer: The correct answer (must match one of the options exactly)
        - chapter: The chapter name (use: {chapter})
        
        IMPORTANT REQUIREMENTS:
        1. The question must be relevant to the chapter content
        2. All 4 options must be plausible but only one correct
        3. The answer must exactly match one of the options
        4. Return ONLY valid JSON, no markdown or extra text
        
        Example format:
        [
          {{
            "question": "What is the main concept discussed in this chapter?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Option A",
            "chapter": "{chapter}"
          }}
        ]
        """
    elif quiz_type == 'topic':
        prompt = f"""
        {SYSTEM_PROMPT}

        Create a quiz with 3 multiple-choice questions for the topic '{topic}' in the chapter '{chapter}' of {subject} at {level} level.
        Each question must:
        - Be derived strictly from the official textbook syllabus.
        - Cover a key concept from the specified topic.
        - Have 4 multiple-choice options.
        - Include the correct answer and the topic it corresponds to.
        Return a JSON list of questions in the format:
        [{{"question": "Sample question?", "options": ["Option 1", "Option 2", "Option 3", "Option 4"], "answer": "Option 1", "topic": "{topic}"}}]
        Return only the JSON list, without any Markdown or code block formatting.
        """
    elif quiz_type == 'chapter':
        prompt = f"""
        {SYSTEM_PROMPT}

        Create a quiz with one multiple-choice question per topic for the following topics in the chapter '{chapter}' of {subject}: {', '.join(topics)}.
        The quiz should be at {level} level.
        Each question must:
        - Be derived strictly from the official textbook syllabus.
        - Cover a key concept from the specified topic.
        - Have 4 multiple-choice options.
        - Include the correct answer and the topic it corresponds to.
        Return a JSON list of questions in the format:
        [{{"question": "Sample question?", "options": ["Option 1", "Option 2", "Option 3", "Option 4"], "answer": "Option 1", "topic": "Topic Name"}}]
        Return only the JSON list, without any Markdown or code block formatting.
        """
    elif quiz_type == 'three_chapter':
        prompt = f"""
        {SYSTEM_PROMPT}

        Create a quiz with 5 multiple-choice questions covering the following chapters in {subject}: {', '.join(chapters)}.
        Each question should:
        - Be derived strictly from the official textbook syllabus.
        - Be designed for 2-3 marks, testing key concepts across the specified chapters.
        - Have 4 multiple-choice options.
        - Include the correct answer and the chapter it corresponds to.
        - Be appropriate for {level} level.
        Return a JSON list of questions in the format:
        [{{"question": "Sample question?", "options": ["Option 1", "Option 2", "Option 3", "Option 4"], "answer": "Option 1", "chapter": "Chapter Name", "marks": 2}}]
        Return only the JSON list, without any Markdown or code block formatting.
        """
    else:
        raise HTTPException(status_code=400, detail="Invalid quiz type")

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=800
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^\s*```json\s*|\s*```$', '', content)
        content = re.sub(r',\s*([\]}])', r'\1', content)
        questions = json.loads(content)
        for q in questions:
            if 'question' not in q or not q['question']:
                q['question'] = f"What is a key concept in {chapter or topic}?"
            if 'options' not in q or len(q['options']) < 4:
                q['options'] = ["A", "B", "C", "D"]
            if 'answer' not in q or not q['answer']:
                q['answer'] = q['options'][0]
            if quiz_type == 'initial' and 'chapter' not in q:
                q['chapter'] = chapter
            if quiz_type in ['topic', 'chapter'] and 'topic' not in q:
                q['topic'] = topic
            if quiz_type == 'three_chapter' and 'marks' not in q:
                q['marks'] = 2
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")

async def generate_study_plan(board: str, class_num: int, subject: str, start_date: str, end_date: str, extra_chapters: List[str] = [], weak_chapters: List[str] = [], user_personality: str = "balanced"):
    syllabus = await get_syllabus(board, class_num, subject)
    if not syllabus or not syllabus.get("chapters"):
        raise HTTPException(status_code=500, detail="Failed to fetch syllabus for study plan")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end - start).days
    total_weeks = max(1, total_days // 7)
    plan = {}
    weak_set = set(weak_chapters + extra_chapters)
    
    all_tasks = []
    for chapter in syllabus["chapters"]:
        chapter_name = chapter["name"]
        time_mult = 2 if chapter_name in weak_set else 1
        for topic in chapter.get("topics", []):
            topic_name = topic["name"] if isinstance(topic, dict) else topic
            subtopics = topic.get("subtopics", []) if isinstance(topic, dict) else await get_subtopics(board, class_num, subject, chapter_name, topic_name)
            for subtopic in subtopics or [topic_name]:
                all_tasks.append({
                    "chapter": chapter_name,
                    "topic": topic_name,
                    "subtopic": subtopic,
                    "time": 1.5 * time_mult,
                    "completed": False,
                    "progress": 0
                })
    
    all_tasks.sort(key=lambda x: (x["chapter"] not in weak_set, x["chapter"], x["topic"], x["subtopic"]))
    
    days_per_week = 5
    tasks_per_day = max(1, len(all_tasks) // (total_weeks * days_per_week))
    task_id = 1
    for i, task in enumerate(all_tasks):
        week_num = str((i // tasks_per_day) + 1)
        day_num = (i % tasks_per_day) % days_per_week + 1
        date = start + timedelta(days=(int(week_num) - 1) * 7 + (day_num - 1))
        if int(week_num) > total_weeks:
            break
        plan[week_num] = plan.get(week_num, [])
        plan[week_num].append({
            "id": task_id,
            "chapter": task["chapter"],
            "topic": task["topic"],
            "subtopic": task["subtopic"],
            "date": date.strftime("%Y-%m-%d"),
            "time": task["time"],
            "difficulty": "Medium",
            "quest_type": "Learning Quest",
            "rewards": "50 XP",
            "description": "Complete this quest to progress",
            "completed": task["completed"],
            "progress": task["progress"]
        })
        task_id += 1

    return plan

def create_fallback_study_plan(subject: str, start_date: str, end_date: str, weak_chapters: List[str]):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end - start).days
    total_weeks = max(1, total_days // 7)
    
    plan = {}
    task_id = 1
    
    for week in range(1, total_weeks + 1):
        week_key = str(week)
        plan[week_key] = []
        
        for day in range(5):
            date = start + timedelta(days=(week - 1) * 7 + day)
            
            if task_id <= 20:
                task = {
                    "id": task_id,
                    "topic": f"Chapter {task_id}",
                    "subject": subject,
                    "subtopic": f"Topic {task_id}",
                    "date": date.strftime("%Y-%m-%d"),
                    "time": 2.0,
                    "difficulty": "Medium",
                    "quest_type": "Learning Quest",
                    "rewards": "50 XP",
                    "description": "Complete this quest to progress in your studies",
                    "completed": False,
                    "progress": 0
                }
                plan[week_key].append(task)
                task_id += 1
    
    return plan

# API Routes
@app.post("/auth/register")
async def register(user_data: UserRegister):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = hash_password(user_data.password)
    
    cursor.execute("""
        INSERT INTO users (first_name, middle_name, last_name, email, password_hash, 
                          role, school_name, child_username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_data.firstName,
        user_data.middleName,
        user_data.lastName,
        user_data.email,
        password_hash,
        user_data.role,
        user_data.schoolName,
        user_data.childUsername
    ))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    token = create_access_token({"sub": str(user_id)})
    user = get_user_by_id(user_id)
    
    return {"token": token, "user": user}

@app.post("/auth/login")
async def login(user_data: UserLogin):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (user_data.email,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not verify_password(user_data.password, result[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(result[0])})
    user = get_user_by_id(result[0])
    
    return {"token": token, "user": user}

@app.get("/auth/me")
async def get_current_user_info(current_user_id: int = Depends(get_current_user)):
    user = get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

SUBJECT_CACHE_FILE = "subject_cache.json"
SYLLABUS_CACHE_FILE = "syllabus_cache.json"

def load_cached_subjects(board, class_num):
    try:
        if os.path.exists(SUBJECT_CACHE_FILE):
            with open(SUBJECT_CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return None
                cache = json.loads(content)
                key = f"{board}_{class_num}"
                if key in cache:
                    return cache[key]
        return None
    except Exception:
        return None

def save_cached_subjects(board, class_num, subjects):
    try:
        cache = {}
        if os.path.exists(SUBJECT_CACHE_FILE):
            with open(SUBJECT_CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    cache = json.loads(content)
        key = f"{board}_{class_num}"
        cache[key] = subjects
        with open(SUBJECT_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass

def load_cached_syllabus(board, class_num, subject):
    try:
        if os.path.exists(SYLLABUS_CACHE_FILE):
            with open(SYLLABUS_CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return None
                cache = json.loads(content)
                key = f"{board}_{class_num}_{subject}"
                if key in cache:
                    return cache[key]
        return None
    except Exception:
        return None

def save_cached_syllabus(board, class_num, subject, syllabus):
    try:
        cache = {}
        if os.path.exists(SYLLABUS_CACHE_FILE):
            with open(SYLLABUS_CACHE_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    cache = json.loads(content)
        key = f"{board}_{class_num}_{subject}"
        cache[key] = syllabus
        with open(SYLLABUS_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass

@app.get("/subjects")
async def get_subjects(board: str, class_num: int):
    cached = load_cached_subjects(board, class_num)
    if cached:
        return cached
    subjects = generate_subjects(board, class_num)
    save_cached_subjects(board, class_num, subjects)
    return subjects

@app.get("/syllabus")
async def get_syllabus_endpoint(
    board: str,
    class_num: int,
    subject: str,
    current_user_id: int = Depends(get_current_user)
):
    return await get_syllabus(board, class_num, subject)

@app.post("/study-plans")
async def create_study_plan(
    plan: StudyPlanRequest,
    current_user_id: int = Depends(get_current_user)
):
    try:
        print(f"Received study plan request: {plan}")
        print(f"Plan data types: subject={type(plan.subject)}, board={type(plan.board)}, class_num={type(plan.class_num)}")
        print(f"Dates: start_date={plan.start_date}, end_date={plan.end_date}")
        print(f"Chapters: extra={plan.extra_chapters}, weak={plan.weak_chapters}")
        print(f"Personality: {plan.personality_type}")
        
        if not plan.subject or not plan.board or not plan.class_num:
            raise HTTPException(status_code=422, detail="Missing required fields: subject, board, or class_num")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM user_preferences WHERE user_id = ?
        """, (current_user_id,))
        
        if cursor.fetchone():
            cursor.execute("""
                UPDATE user_preferences 
                SET board = ?, class_num = ?, personality_type = ?
                WHERE user_id = ?
            """, (plan.board, plan.class_num, plan.personality_type, current_user_id))
        else:
            cursor.execute("""
                INSERT INTO user_preferences (user_id, board, class_num, personality_type)
                VALUES (?, ?, ?, ?)
            """, (current_user_id, plan.board, plan.class_num, plan.personality_type))
        
        plan_data = await generate_study_plan(
            plan.board,
            plan.class_num,
            plan.subject,
            plan.start_date,
            plan.end_date,
            plan.extra_chapters,
            plan.weak_chapters,
            plan.personality_type
        )
        
        cursor.execute("""
            INSERT INTO study_plans (user_id, subject, board, class_num, plan_data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user_id,
            plan.subject,
            plan.board,
            plan.class_num,
            json.dumps(plan_data)
        ))
        
        conn.commit()
        conn.close()
        
        return {"message": "Study plan created successfully", "plan_data": plan_data}
    except Exception as e:
        print(f"Error creating study plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating study plan: {str(e)}")

@app.get("/study-plans")
async def get_study_plans(current_user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM study_plans WHERE user_id = ?", (current_user_id,))
    plans = cursor.fetchall()
    conn.close()
    
    result = []
    for plan in plans:
        result.append({
            "id": plan[0],
            "subject": plan[2],
            "board": plan[3],
            "class_num": plan[4],
            "plan_data": json.loads(plan[5]),
            "created_at": plan[6]
        })
    
    return result

@app.get("/user-preferences")
async def get_user_preferences(current_user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT board, class_num, personality_type 
        FROM user_preferences 
        WHERE user_id = ?
    """, (current_user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "board": result[0],
            "class_num": result[1],
            "personality_type": result[2]
        }
    return None

@app.get("/study-plans/{subject}")
async def get_study_plan_by_subject(
    subject: str,
    current_user_id: int = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM study_plans 
        WHERE user_id = ? AND subject = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (current_user_id, subject))
    
    plan = cursor.fetchone()
    conn.close()
    
    if plan:
        return {
            "id": plan[0],
            "subject": plan[2],
            "board": plan[3],
            "class_num": plan[4],
            "plan_data": json.loads(plan[5]),
            "created_at": plan[6]
        }
    raise HTTPException(status_code=404, detail="Study plan not found for this subject")

@app.put("/progress")
async def update_progress(
    progress: ProgressUpdate,
    current_user_id: int = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM progress WHERE user_id = ? AND task_id = ?",
        (current_user_id, progress.task_id)
    )
    
    if cursor.fetchone():
        cursor.execute("""
            UPDATE progress 
            SET completed = ?, score = ?, completed_at = ?
            WHERE user_id = ? AND task_id = ?
        """, (
            progress.completed,
            progress.score,
            datetime.utcnow() if progress.completed else None,
            current_user_id,
            progress.task_id
        ))
    else:
        cursor.execute("""
            INSERT INTO progress (user_id, task_id, completed, score, completed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            current_user_id,
            progress.task_id,
            progress.completed,
            progress.score,
            datetime.utcnow() if progress.completed else None
        ))
    
    conn.commit()
    conn.close()
    
    return {"message": "Progress updated successfully"}

@app.put("/task-progress")
async def update_task_progress(
    task_progress: TaskProgressUpdate,
    current_user_id: int = Depends(get_current_user)
):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT plan_data FROM study_plans 
            WHERE user_id = ? AND subject = ?
            ORDER BY created_at DESC LIMIT 1
        """, (current_user_id, task_progress.subject))
        
        plan_result = cursor.fetchone()
        if not plan_result:
            raise HTTPException(status_code=404, detail="Study plan not found")
        
        plan_data = json.loads(plan_result[0])
        
        if task_progress.week in plan_data:
            for task in plan_data[task_progress.week]:
                if task["id"] == task_progress.task_id:
                    task["completed"] = task_progress.completed
                    task["progress"] = task_progress.progress
                    if task_progress.score is not None:
                        task["score"] = task_progress.score
                    break
        
        cursor.execute("""
            UPDATE study_plans 
            SET plan_data = ?
            WHERE user_id = ? AND subject = ?
            ORDER BY created_at DESC LIMIT 1
        """, (json.dumps(plan_data), current_user_id, task_progress.subject))
        
        conn.commit()
        conn.close()
        
        return {"message": "Task progress updated successfully", "plan_data": plan_data}
        
    except Exception as e:
        print(f"Error updating task progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating task progress: {str(e)}")

@app.get("/progress")
async def get_progress(current_user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM progress WHERE user_id = ?", (current_user_id,))
    progress_records = cursor.fetchall()
    conn.close()
    
    result = []
    for record in progress_records:
        result.append({
            "id": record[0],
            "task_id": record[2],
            "completed": record[3],
            "score": record[4],
            "completed_at": record[5]
        })
    
    return result

@app.get("/dashboard/stats")
async def get_dashboard_stats(current_user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM progress WHERE user_id = ? AND completed = TRUE",
        (current_user_id,)
    )
    completed_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM progress WHERE user_id = ?", (current_user_id,))
    total_tasks = cursor.fetchone()[0]
    
    cursor.execute(
        "SELECT score FROM progress WHERE user_id = ? AND score IS NOT NULL",
        (current_user_id,)
    )
    scores = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    average_score = sum(scores) / len(scores) if scores else 0.0
    streak_days = 8
    
    return {
        "completed_tasks": completed_tasks,
        "total_tasks": max(total_tasks, 50),
        "streak_days": streak_days,
        "total_points": 1250 + (completed_tasks * 10),
        "weekly_goal": 15,
        "completed_this_week": min(completed_tasks, 12),
        "average_score": round(average_score, 1)
    }

@app.post("/quizzes")
async def create_quiz(
    quiz_request: QuizRequest,
    current_user_id: int = Depends(get_current_user)
):
    if quiz_request.mode == 'initial' and quiz_request.chapters:
        questions = await generate_quiz_questions(quiz_request.subject, '', '', quiz_request.level, 'initial', quiz_request.chapters)
    elif quiz_request.mode == 'topic' and quiz_request.chapter and quiz_request.topic:
        questions = await generate_quiz_questions(quiz_request.subject, quiz_request.chapter, quiz_request.topic, quiz_request.level, 'topic')
    elif quiz_request.mode == 'chapter' and quiz_request.chapter and quiz_request.topics:
        questions = await generate_quiz_questions(quiz_request.subject, quiz_request.chapter, '', quiz_request.level, 'chapter', [], quiz_request.topics)
    elif quiz_request.mode == 'three_chapter' and quiz_request.chapters:
        questions = await generate_quiz_questions(quiz_request.subject, '', '', quiz_request.level, 'three_chapter', quiz_request.chapters)
    else:
        questions = await generate_quiz_questions(quiz_request.subject, quiz_request.chapter, quiz_request.topic, quiz_request.level)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quizzes (user_id, subject, chapter, topic, question_data)
        VALUES (?, ?, ?, ?, ?)
    """, (
        current_user_id,
        quiz_request.subject,
        quiz_request.chapter or '',
        quiz_request.topic or '',
        json.dumps(questions)
    ))
    conn.commit()
    conn.close()
    
    return {"questions": questions}

@app.get("/quizzes")
async def get_quizzes(current_user_id: int = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM quizzes WHERE user_id = ?", (current_user_id,))
    quizzes = cursor.fetchall()
    conn.close()
    
    result = []
    for quiz in quizzes:
        result.append({
            "id": quiz[0],
            "subject": quiz[2],
            "chapter": quiz[3],
            "topic": quiz[4],
            "question_data": json.loads(quiz[5]),
            "created_at": quiz[6]
        })
    
    return result

@app.get("/subtopics")
async def get_subtopics_request(
    board: str,
    class_num: int,
    subject: str,
    chapter: str,
    topic: str,
    current_user_id: int = Depends(get_current_user)
):
    return {"subtopics": get_subtopics(board, class_num, subject, chapter, topic)}

@app.post("/chat")
async def chat_request(
    chat_req: ChatRequest,
    current_user_id: int = Depends(get_current_user)
):
    prompt = f"""
    {SYSTEM_PROMPT}

    The student asked: "{chat_req.message}" for the subtopic '{chat_req.subtopic}' in the topic '{chat_req.topic}' of the chapter '{chat_req.chapter}' in {chat_req.board} Class {chat_req.class_num} {chat_req.subject}.
    Provide a response following the four-part structure if it's a concept question, or answer appropriately if it's a practice question or clarification request, framing it as part of the "{chat_req.subtopic} Quest".
    Return only the response text, without any Markdown or code block formatting.
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1000
        )
        content = response.choices[0].message.content.strip()
        return {"response": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.put("/reschedule")
async def reschedule(
    reschedule_req: RescheduleRequest,
    current_user_id: int = Depends(get_current_user)
):
    plan = reschedule_plan(current_user_id, reschedule_req.subject, reschedule_req.missed_date)
    return {"plan_data": plan}

@app.post("/auth/logout")
async def logout(current_user_id: int = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

@app.post("/explanation")
async def get_explanation(
    explanation_request: ExplanationRequest,
    current_user_id: int = Depends(get_current_user)
):
    target = explanation_request.topic or explanation_request.chapter
    quest_name = f"Conquer {target} Quest"
    prompt = f"""
    {SYSTEM_PROMPT}

    Explain the concept '{target}' for {explanation_request.board} Class {explanation_request.class_num} {explanation_request.subject} as per the official curriculum (NCERT for CBSE, SCERT Telangana for BSE Telangana, CISCE for ICSE/ISC).
    Frame the explanation as part of a story-based quest called \"{quest_name}\" to engage the student.
    Follow the four-part structure:
    1. Start with a detailed, engaging real-life example that illustrates the concept, integrated into the quest narrative (e.g., 'As a brave explorer in the Algebra Kingdom, you encounter...').
    2. Provide the textbook definition or explanation, including any formulas or key notes, presented as a discovery in the quest.
    3. Include a detailed additional example aligned with the textbook style, continuing the quest narrative.
    4. End with an understanding check: 'Does this make sense, or should I explain it another way?' followed by a short, syllabus-based quiz question framed as a quest challenge (e.g., 'Quest Challenge: Solve this to unlock the next gate...').
    Return only the explanation text, without any Markdown or code block formatting.
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1000
        )
        content = response.choices[0].message.content.strip()
        return {"explanation": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating explanation: {str(e)}")

@app.post("/image")
async def generate_image(
    image_request: ImageRequest,
    current_user_id: int = Depends(get_current_user)
):
    target = image_request.subtopic if image_request.subtopic else image_request.topic
    prompt = f"A clear, educational illustration for {target} in a high school {image_request.subject} context, suitable for a textbook, colorful and engaging for students, avoiding any text or complex details."
    try:
        response = await openai.Image.acreate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = response['data'][0]['url']
        return {"image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

@app.get("/")
async def root():
    return {"message": "AI Study Tutor API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
