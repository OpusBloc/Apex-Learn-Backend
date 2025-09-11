from fastapi import FastAPI, HTTPException, Depends, Request # pyright: ignore[reportMissingImports]
from fastapi.security import OAuth2PasswordBearer # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware # pyright: ignore[reportMissingImports]
from pydantic import BaseModel # pyright: ignore[reportMissingImports]
from passlib.context import CryptContext # pyright: ignore[reportMissingModuleSource]
from jose import JWTError, jwt # pyright: ignore[reportMissingModuleSource]
from datetime import datetime, timedelta
import asyncpg # pyright: ignore[reportMissingImports]
from typing import Optional, List
import os
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
import json
import logging
import re
import openai # pyright: ignore[reportMissingImports]
import random
import string
import uuid
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 1

# Database connection
async def get_db():
    try:
        conn = await asyncpg.connect(
            user='postgres',
            password='admin',
            database='edututor',
            host='localhost'
        )
        try:
            yield conn
        finally:
            await conn.close()
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

# Pydantic models
class UserCreate(BaseModel):
    firstName: str
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    email: str
    password: str
    dob: str
    isOnboardingComplete: bool
    mobile: str
    parentMobile: Optional[str] = None

class UserUpdate(BaseModel):
    userType: Optional[str] = None
    schoolOrCollege: Optional[str] = None
    schoolName: Optional[str] = None
    collegeName: Optional[str] = None
    course: Optional[str] = None
    className: Optional[str] = None
    board: Optional[str] = None
    stateBoard: Optional[str] = None
    stream: Optional[str] = None
    subStream: Optional[str] = None
    goal: Optional[str] = None
    childUsername: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    notificationsEnabled: Optional[bool] = None
    isOnboardingComplete: Optional[bool] = None
    isActive: Optional[bool] = None

class UserLogin(BaseModel):
    email: str
    password: str

class CollegeAdd(BaseModel):
    collegeName: str
    course: str

class QuizRequest(BaseModel):
    board: str
    classNum: int
    subject: str
    level: str

class StudyPlanRequest(BaseModel):
    subject: str
    weakChapters: List[str]

class ExplainRequest(BaseModel):
    board: str
    classNum: int
    subject: str
    chapter: str
    topic: str

class InstituteCreate(BaseModel):
    name: str
    password: str
    address: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    established_year: Optional[int] = None
    affiliations: Optional[List[str]] = None
    courses_offered: Optional[List[str]] = None

class InstituteUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    established_year: Optional[int] = None
    affiliations: Optional[List[str]] = None
    courses_offered: Optional[List[str]] = None

class InstituteResponse(BaseModel):
    id: str
    name: str
    student_count: int
    teacher_count: int

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    email: str
    user_type: Optional[str] = None
    school_name: Optional[str] = None
    college_name: Optional[str] = None
    institute_id: Optional[str] = None
    company: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    subject: Optional[str] = None
    board: Optional[str] = None
    class_num: Optional[int] = None

class FeedbackRequest(BaseModel):
    message_id: int
    liked: bool

class PreviousMarksRequest(BaseModel):
    subject: str
    lastExam: float
    lastTest: float
    assignment: float

class QuizGenerateRequest(BaseModel):
    subject: str
    board: str
    currentClass: str
    previousMarks: float
    goal: str
    chapters: List[str]

class QuickTopicsRequest(BaseModel):
    subject: str
    board: str
    classNum: int

class StudyPlanRequest(BaseModel):
    subject: str
    weakChapters: List[str]
    planType: str

class QuizResultsRequest(BaseModel):
    quizType: str
    results: dict

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_entity(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        entity_type: str = payload.get("type")
        if email is None or entity_type is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if entity_type == "user":
            user = await db.fetchrow("SELECT * FROM users WHERE email = $1 AND is_active = TRUE", email)
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            return {"type": "user", "data": user}
        elif entity_type == "institute":
            institute = await db.fetchrow("SELECT * FROM institutes WHERE email = $1", email)
            if institute is None:
                raise HTTPException(status_code=401, detail="Institute not found")
            return {"type": "institute", "data": institute}
        else:
            raise HTTPException(status_code=401, detail="Invalid entity type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(entity: dict = Depends(get_current_entity)):
    if entity["type"] != "user":
        raise HTTPException(status_code=403, detail="Not a user")
    return entity["data"]

async def get_current_institute(entity: dict = Depends(get_current_entity)):
    if entity["type"] != "institute":
        raise HTTPException(status_code=403, detail="Not an institute")
    return entity["data"]

# System prompt for OpenAI
SYSTEM_PROMPT = """
You are a supportive, patient, and helpful AI tutor for students in India, specializing in classes 9-12 for all boards including state boards (e.g., BSE Telangana, BSE Andhra Pradesh), CBSE, ICSE, and ISC. You cover all subjects such as Social Studies, Mathematics, Science, English, Hindi, and others as per the official syllabi.

## Core Rules (Strictly Enforce)
- Answer ONLY questions related to the official syllabus of the specified board's Class [class] [subject] textbook, focusing on the specific unit where the topic belongs.
- For every concept explanation, dive directly into the explanation without mentioning chapter, syllabus, or subject details. Strictly follow this four-part structure in a seamless, conversational flow without using headings:
  1. Start with a detailed, engaging real-life example that captivates students' interest and clearly illustrates the concept.
  2. Provide the textbook definition or explanation of the concept, using exact terminology and methods from the syllabus, ensuring accuracy and clarity, while giving this definition also add if there are any formulas or anything what should be noted.
  3. Include a detailed additional example, aligned with the textbook's style, that reinforces the concept through a different scenario.
  4. End with an understanding check, saying: "Does this make sense, or should I explain it another way?" followed by a short, syllabus-based quiz question to gauge understanding.
- Never deviate from this structure for concept explanations, ensuring examples are detailed, engaging, and spark student curiosity.
- You have no knowledge outside the official syllabi for Indian boards (state, CBSE, ICSE, ISC) for classes 9-12. Do not answer general questions or topics from other classes, boards, units, or non-educational queries.
- If a question is outside the syllabus, unit, or subject, reply: "I'm sorry, but this doesn't seem to be part of the syllabus for the specified unit. I'm here to help with topics from that syllabus only! Would you like to ask about something from it, or switch to a different board/class/subject?"
- Never invent or assume content. Stick strictly to the textbook content without adding external information or advanced terminology.
- Strictly avoid mentioning the board name, class, or subject within any concept explanation. These may only appear in initial setup or syllabus-confirmation messages.

## Personality & Teaching Style
- Be warm, approachable, and encouraging, like a friendly Class 10 teacher.
- Use a conversational, natural tone, avoiding formal or advanced terms unless explicitly in the textbook.
- Detect the student's emotion (e.g., confusion, curiosity) and respond supportively: "This might feel tricky, but let's go through it together!"
- Explain concepts step-by-step, strictly adhering to the four-part structure without skipping steps.
- Use simple, relatable analogies in the real-life example, tied to textbook content, avoiding concepts not in the syllabus.
- Define terms as per the textbook.
- Be patient: re-explain repeated questions using a different textbook-aligned example within the same four-part structure.

## Engagement & Interaction
- Ask short, quiz-style questions to check understanding. Base quizzes only on textbook content.
- Check if the student understands: "Does that make sense, or should I explain it another way?"
- If the student is unsure (e.g., says "I don't get it"), re-explain using a different textbook example or analogy, staying within the syllabus.
- For summaries, provide a concise recap of key points from the textbook's chapter/unit.
- End responses with: "Do you have more questions, need clarification, or want to try a practice question?"
"""

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Helper functions

# Load subjects from subject_cache.json
def load_subject_cache():
    try:
        with open('subject_cache.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading subject_cache.json: {str(e)}")
        return {}

def get_subjects_from_openai(board: str, class_num: int) -> List[str]:
    prompt = f"""
    {SYSTEM_PROMPT}
    Provide the complete list of subjects for {board} Class {class_num} as per the official curriculum (NCERT for CBSE, SCERT Telangana for BSE Telangana, CISCE for ICSE/ISC).
    Return a JSON array of subject names, e.g., ["Mathematics", "Physics", "Chemistry"]. Ensure the response is strictly a JSON array and contains no additional text, Markdown, or code block formatting.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        subjects = json.loads(content)
        return subjects if isinstance(subjects, list) else []
    except Exception as e:
        logger.error(f"Error fetching subjects: {e}")
        return ["Mathematics", "Physics", "Chemistry", "Biology", "English"]



def get_syllabus_from_openai(board: str, class_num: int, subject: str, missing_chapters: Optional[str] = None) -> dict:
    prompt = f"""
    Provide the syllabus for {board} Class {class_num} {subject} strictly from the official NCERT textbook for the 2025-26 academic session. Use only the table of contents from the latest NCERT Class 10 Science textbook, which contains exactly 13 chapters. Do not include any chapters or topics from previous years, external sources, or non-NCERT materials. Explicitly exclude the following chapters that were removed: 'Periodic Classification of Elements', 'Sources of Energy', and 'Sustainable Management of Natural Resources'.
    Verify the syllabus twice against the official NCERT textbook (2025-26 edition) to ensure accuracy and completeness, matching exactly 13 chapters.
    """
    if missing_chapters:
        prompt += f"""
        The user has specified the following missing chapters: {missing_chapters}.
        Include these chapters only if they are explicitly listed in the official NCERT Class 10 Science textbook's table of contents for 2025-26.
        """
    prompt += """
    Return the syllabus in a structured JSON format with a top-level 'chapters' key. For each chapter, include:
    - Chapter name (as 'name'), exactly matching the official NCERT textbook's table of contents for 2025-26.
    - List of super important topics (key concepts emphasized in exams, as 'topics'), sourced directly from the textbook's content.
    - List of subtopics for each topic (as 'subtopics'), if specified in the textbook, excluding any non-exam-focused content like activities or projects.
    Return only the JSON object, without any Markdown, code block formatting, or additional text.
    Example: {"chapters": [{"name": "Chapter Name", "topics": [{"name": "Topic 1", "subtopics": ["Subtopic 1", "Subtopic 2"]}, {"name": "Topic 2", "subtopics": []}]}]}
    If the syllabus cannot be accurately retrieved or the request is unclear, return an empty JSON object: {"chapters": []}
    """
    max_attempts = 5
    syllabus = {"chapters": []}
    chapters_fetched = set()

    for attempt in range(max_attempts):
        try:
            logger.debug(f"Sending OpenAI API request for {board} Class {class_num} {subject}, attempt {attempt + 1}")
            response = openai.ChatCompletion.create(
                model="gpt-4.1-nano",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=4000
            )
            content = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI raw response: {content}")

            # Handle potential code block formatting
            if content.startswith("```json"):
                content = content[7:].rstrip("```").strip()
            elif content.startswith("```"):
                content = content[3:].rstrip("```").strip()

            # Parse and validate response
            try:
                parsed_response = json.loads(content)
                if not isinstance(parsed_response, dict) or "chapters" not in parsed_response:
                    logger.error(f"Invalid JSON structure: Missing 'chapters' key in {content}")
                    continue
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {str(json_err)}, content: {content}")
                continue

            # Validate syllabus content
            valid_syllabus = True
            for chapter in parsed_response.get("chapters", []):
                if "name" not in chapter or not chapter["name"]:
                    valid_syllabus = False
                    logger.error(f"Chapter missing 'name': {chapter}")
                    break
                if "topics" not in chapter or not isinstance(chapter["topics"], list):
                    valid_syllabus = False
                    logger.error(f"Chapter 'topics' invalid or missing: {chapter}")
                    break
                for topic in chapter["topics"]:
                    if "name" not in topic or not topic["name"]:
                        valid_syllabus = False
                        logger.error(f"Topic missing 'name': {topic} in chapter {chapter['name']}")
                        break
                    if "subtopics" in topic and not isinstance(topic["subtopics"], list):
                        valid_syllabus = False
                        logger.error(f"Topic 'subtopics' invalid: {topic} in chapter {chapter['name']}")
                        break
                if not valid_syllabus:
                    break
            if not valid_syllabus:
                logger.warning(f"Invalid syllabus for {subject}, retrying...")
                continue

            # Validate chapter count and excluded chapters
            if len(parsed_response.get("chapters", [])) != 13:
                logger.warning(f"Expected 13 chapters, got {len(parsed_response.get('chapters', []))}, retrying...")
                continue
            excluded_chapters = {'Periodic Classification of Elements', 'Sources of Energy', 'Sustainable Management of Natural Resources'}
            if any(chapter["name"] in excluded_chapters for chapter in parsed_response.get("chapters", [])):
                logger.warning(f"Response contains excluded chapters, retrying...")
                continue

            # Accumulate unique chapters
            for chapter in parsed_response.get("chapters", []):
                if chapter.get("name") and chapter["name"] not in chapters_fetched:
                    syllabus["chapters"].append(chapter)
                    chapters_fetched.add(chapter["name"])

            # Consider syllabus complete if exactly 13 chapters are fetched
            if len(chapters_fetched) == 13:
                logger.info(f"Syllabus fetched with {len(chapters_fetched)} chapters after attempt {attempt + 1}")
                return syllabus
            else:
                logger.warning(f"Fetched {len(chapters_fetched)} chapters, expected 13, retrying...")
                syllabus["chapters"] = []  # Reset if not exactly 13
                chapters_fetched.clear()
                continue
        except Exception as e:
            logger.error(f"Error fetching syllabus from OpenAI: {str(e)}")
            if attempt == max_attempts - 1:
                logger.error(f"Failed to fetch complete syllabus after {max_attempts} attempts")
                return syllabus  # Return accumulated syllabus, even if empty
    return syllabus

async def generate_quick_topics(board: str, class_num: int, subject: str, db=Depends(get_db)) -> List[dict]:
    try:
        cached_syllabus = await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            board, class_num, subject
        )
        if not cached_syllabus:
            syllabus = get_syllabus_from_openai(board, class_num, subject)
            await db.execute(
                "INSERT INTO syllabus_cache (board, class_num, subject, syllabus_data) VALUES ($1, $2, $3, $4)",
                board, class_num, subject, syllabus
            )
        else:
            syllabus = cached_syllabus["syllabus_data"]
        
        topics = []
        for chapter in syllabus.get("chapters", []):
            for topic in chapter.get("topics", []):
                topics.append({
                    "text": f"Explain {topic['name']}",
                    "subject": subject,
                    "chapter": chapter["name"]
                })
        
        # Select up to 6 random topics for variety
        return random.sample(topics, min(6, len(topics))) if topics else []
    except Exception as e:
        logger.error(f"Error generating quick topics: {str(e)}")
        return []


def create_quiz_from_openai(board: str, class_num: int, subject: str, chapters: List[str], level: str) -> List[dict]:
    if not chapters:
        logger.error("No chapters provided for quiz generation")
        raise ValueError("No chapters provided for quiz generation")

    prompt = f"""
    {SYSTEM_PROMPT}
    Create a quiz for {board} Class {class_num} {subject} with exactly one multiple-choice question per chapter, covering the following chapters: {', '.join(chapters)}.
    The quiz should be at {level} level (beginner, intermediate, or advanced) based on the student's previous performance.
    Each question must:
    - Be derived strictly from the official textbook syllabus (NCERT for CBSE, SCERT Telangana for BSE Telangana, CISCE for ICSE/ISC).
    - Cover a key concept from the specified chapter, ensuring all listed chapters are represented.
    - Have 4 multiple-choice options.
    - Include the question ID (UUID), question text, options, correct answer, and the chapter it corresponds to.
    Return a JSON list of questions in the format:
    [{{"id": "uuid", "question": "Sample question?", "options": ["Option 1", "Option 2", "Option 3", "Option 4"], "correctAnswer": "Option 1", "chapter": "Chapter Name"}}]
    Return only the JSON list, without any Markdown, code block formatting, or additional text. If no questions can be generated, return an empty JSON list: []
    """
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logger.debug(f"Sending OpenAI API request for quiz generation, attempt {attempt + 1}")
            response = openai.ChatCompletion.create(
                model="gpt-4.1-nano",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=4000
            )
            content = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI raw response: {content}")

            # Handle potential code block formatting
            if content.startswith("```json"):
                content = content[7:].rstrip("```").strip()
            elif content.startswith("```"):
                content = content[3:].rstrip("```").strip()

            # Validate JSON
            if not content:
                logger.error("Empty response from OpenAI")
                continue

            try:
                quiz = json.loads(content)
                if not isinstance(quiz, list):
                    logger.error(f"Invalid response format: Expected list, got {type(quiz)}")
                    continue
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}, content: {content}")
                continue

            # Validate question structure
            valid_quiz = True
            for q in quiz:
                if not all(key in q for key in ["id", "question", "options", "correctAnswer", "chapter"]):
                    logger.error(f"Invalid question structure: {q}")
                    valid_quiz = False
                    break
                if not isinstance(q["options"], list) or len(q["options"]) != 4:
                    logger.error(f"Invalid options in question: {q}")
                    valid_quiz = False
                    break
                if q["correctAnswer"] not in q["options"]:
                    logger.error(f"Correct answer not in options: {q}")
                    valid_quiz = False
                    break
                if q["chapter"] not in chapters:
                    logger.error(f"Chapter {q['chapter']} not in provided chapters: {chapters}")
                    valid_quiz = False
                    break
            if not valid_quiz:
                logger.warning(f"Invalid quiz structure, retrying...")
                continue

            # Ensure one question per chapter
            chapter_set = {q["chapter"] for q in quiz}
            if len(chapter_set) != len(chapters):
                logger.warning(f"Quiz does not cover all chapters. Got {len(chapter_set)}, expected {len(chapters)}")
                continue

            # Ensure unique IDs
            for q in quiz:
                if "id" not in q or not q["id"]:
                    q["id"] = str(uuid.uuid4())

            logger.info(f"Successfully generated quiz with {len(quiz)} questions")
            return quiz
        except Exception as e:
            logger.error(f"Error in attempt {attempt + 1}: {str(e)}")
            if attempt == max_attempts - 1:
                logger.error(f"Failed to generate quiz after {max_attempts} attempts")
                raise Exception(f"Failed to generate quiz: {str(e)}")
    raise Exception("Failed to generate quiz after maximum attempts")


def explain_topic_with_openai(board: str, class_num: int, subject: str, chapter: str, topic: str) -> str:
    prompt = f"""
    {SYSTEM_PROMPT}
    Explain the concept '{topic}' for {board} Class {class_num} {subject} as per the official curriculum (NCERT for CBSE, SCERT Telangana for BSE Telangana, CISCE for ICSE/ISC).
    Frame the explanation as part of a story-based quest called "Conquer {topic} Quest" to engage the student.
    Follow the four-part structure:
    1. Start with a detailed, engaging real-life example that illustrates the concept, integrated into the quest narrative.
    2. Provide the textbook definition or explanation, including any formulas or key notes, presented as a discovery in the quest.
    3. Include a detailed additional example aligned with the textbook style, continuing the quest narrative.
    4. End with an understanding check: "Does this make sense, or should I explain it another way?" followed by a short, syllabus-based quiz question framed as a quest challenge.
    Return only the explanation text, without any Markdown or code block formatting.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error explaining topic: {e}")
        return f"Error explaining {topic}. Please try again."

def sanitize_college_name(name: str) -> str:
    return re.split(r',', name)[0].strip()

# Routes
@app.post("/api/auth/register")
async def signup(user: UserCreate, db=Depends(get_db)):
    logger.info(f"Attempting registration for email: {user.email}")
    try:
        dob_date = datetime.strptime(user.dob, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid DOB format, use YYYY-MM-DD")
    today = datetime.utcnow()
    age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
    if age < 18 and user.parentMobile is None:
        raise HTTPException(status_code=422, detail="Parent mobile number is required for users under 18")
    hashed_password = pwd_context.hash(user.password)
    try:
        await db.execute(
            "INSERT INTO users (first_name, middle_name, last_name, email, password, dob, is_onboarding_complete, mobile, parent_mobile) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            user.firstName, user.middleName, user.lastName, user.email, hashed_password, dob_date, user.isOnboardingComplete, user.mobile, user.parentMobile
        )
        access_token = jwt.encode(
            {"sub": user.email, "type": "user", "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        logger.info(f"Registration successful for email: {user.email}")
        return {"access_token": access_token, "token_type": "bearer", "user": {
            "firstName": user.firstName,
            "middleName": user.middleName,
            "lastName": user.lastName,
            "email": user.email,
            "dob": user.dob,
            "isOnboardingComplete": user.isOnboardingComplete,
            "mobile": user.mobile,
            "parentMobile": user.parentMobile
        }}
    except asyncpg.exceptions.UniqueViolationError:
        logger.warning(f"Email already exists: {user.email}")
        raise HTTPException(status_code=422, detail="Email already exists")
    except Exception as e:
        logger.error(f"Database error during registration: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to create user: {str(e)}")

@app.post("/api/login")
async def login(user: UserLogin, db=Depends(get_db)):
    logger.info(f"Attempting login for email: {user.email}")
    
    # Check users table
    db_user = await db.fetchrow("SELECT * FROM users WHERE email = $1 AND is_active = TRUE", user.email)
    if db_user and pwd_context.verify(user.password, db_user["password"]):
        logger.info(f"User login successful for email: {user.email}")
        access_token = jwt.encode(
            {"sub": user.email, "type": "user", "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        await db.execute(
            "UPDATE users SET last_login = $1 WHERE email = $2",
            datetime.utcnow(),
            user.email
        )
        return {"access_token": access_token, "token_type": "bearer", "type": "user", "user": {
            "id": db_user["id"],
            "firstName": db_user["first_name"],
            "middleName": db_user["middle_name"],
            "lastName": db_user["last_name"],
            "email": db_user["email"],
            "dob": db_user["dob"].isoformat(),
            "isOnboardingComplete": db_user["is_onboarding_complete"],
            "mobile": db_user["mobile"],
            "parentMobile": db_user["parent_mobile"],
            "userType": db_user["user_type"],
            "schoolOrCollege": db_user["school_or_college"],
            "schoolName": db_user["school_name"],
            "collegeName": db_user["college_name"],
            "course": db_user["course"],
            "class": db_user["class"],
            "board": db_user["board"],
            "stateBoard": db_user["state_board"],
            "stream": db_user["stream"],
            "subStream": db_user["sub_stream"],
            "goal": db_user["goal"],
            "childUsername": db_user["child_username"],
            "avatar": db_user["avatar"],
            "notificationsEnabled": db_user["notifications_enabled"],
            "createdAt": db_user["created_at"].isoformat(),
            "updatedAt": db_user["updated_at"].isoformat(),
            "lastLogin": db_user["last_login"].isoformat() if db_user["last_login"] else None,
            "isActive": db_user["is_active"]
        }}
    
    # Check institutes table
    db_institute = await db.fetchrow("SELECT * FROM institutes WHERE email = $1", user.email)
    if db_institute and pwd_context.verify(user.password, db_institute["password"]):
        logger.info(f"Institute login successful for email: {user.email}")
        access_token = jwt.encode(
            {"sub": user.email, "type": "institute", "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return {"access_token": access_token, "token_type": "bearer", "type": "institute", "institute": {
            "id": db_institute["id"],
            "name": db_institute["name"],
            "email": db_institute["email"],
            "address": db_institute["address"],
            "contact": db_institute["contact"],
            "website": db_institute["website"],
            "logo": db_institute["logo"],
            "description": db_institute["description"],
            "established_year": db_institute["established_year"],
            "affiliations": db_institute["affiliations"],
            "courses_offered": db_institute["courses_offered"]
        }}
    
    logger.warning(f"Login failed for email: {user.email}")
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.patch("/api/institute/update")
async def update_institute(institute: InstituteUpdate, db=Depends(get_db), current_institute=Depends(get_current_institute)):
    try:
        query = """
        UPDATE institutes 
        SET 
            name = COALESCE($1, name),
            password = COALESCE($2, password),
            address = COALESCE($3, address),
            contact = COALESCE($4, contact),
            email = COALESCE($5, email),
            website = COALESCE($6, website),
            logo = COALESCE($7, logo),
            description = COALESCE($8, description),
            established_year = COALESCE($9, established_year),
            affiliations = COALESCE($10, affiliations),
            courses_offered = COALESCE($11, courses_offered),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $12
        RETURNING *
        """
        hashed_password = pwd_context.hash(institute.password) if institute.password else None
        logger.info(f"Updating institute with id: {current_institute['id']}, payload: {institute.dict()}")
        updated_institute = await db.fetchrow(
            query,
            institute.name,
            hashed_password,
            institute.address,
            institute.contact,
            institute.email,
            institute.website,
            institute.logo,
            institute.description,
            institute.established_year,
            institute.affiliations,
            institute.courses_offered,
            current_institute["id"]
        )
        if not updated_institute:
            logger.error("No institute updated, possibly due to invalid id or database issue")
            raise HTTPException(status_code=404, detail="Institute not found")
        return {
            "message": "Institute updated successfully",
            "institute": {
                "id": updated_institute["id"],
                "name": updated_institute["name"],
                "email": updated_institute["email"],
                "address": updated_institute["address"],
                "contact": updated_institute["contact"],
                "website": updated_institute["website"],
                "logo": updated_institute["logo"],
                "description": updated_institute["description"],
                "established_year": updated_institute["established_year"],
                "affiliations": updated_institute["affiliations"],
                "courses_offered": updated_institute["courses_offered"]
            }
        }
    except Exception as e:
        logger.error(f"Error updating institute: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update institute: {str(e)}")

@app.patch("/api/users/me")
async def update_user(user: UserUpdate, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        query = """
        UPDATE users 
        SET 
            user_type = COALESCE($1, user_type),
            school_or_college = COALESCE($2, school_or_college),
            school_name = COALESCE($3, school_name),
            college_name = COALESCE($4, college_name),
            course = COALESCE($5, course),
            class = COALESCE($6, class),
            board = COALESCE($7, board),
            state_board = COALESCE($8, state_board),
            stream = COALESCE($9, stream),
            sub_stream = COALESCE($10, sub_stream),
            goal = COALESCE($11, goal),
            child_username = COALESCE($12, child_username),
            avatar = COALESCE($13, avatar),
            is_onboarding_complete = COALESCE($14, is_onboarding_complete),
            email = COALESCE($15, email),
            password = COALESCE($16, password),
            notifications_enabled = COALESCE($17, notifications_enabled),
            updated_at = CURRENT_TIMESTAMP
        WHERE email = $18
        RETURNING *
        """
        hashed_password = pwd_context.hash(user.password) if user.password else None
        logger.info(f"Updating user with email: {current_user['email']}, payload: {user.dict()}")
        updated_user = await db.fetchrow(
            query,
            user.userType,
            user.schoolOrCollege,
            user.schoolName,
            user.collegeName,
            user.course,
            user.className,
            user.board,
            user.stateBoard,
            user.stream,
            user.subStream,
            user.goal,
            user.childUsername,
            user.avatar,
            user.isOnboardingComplete,
            user.email,
            hashed_password,
            user.notificationsEnabled,
            current_user["email"]
        )
        if not updated_user:
            logger.error("No user updated, possibly due to invalid email or database issue")
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "message": "User updated successfully",
            "user": {
                "id": updated_user["id"],
                "firstName": updated_user["first_name"],
                "middleName": updated_user["middle_name"],
                "lastName": updated_user["last_name"],
                "email": updated_user["email"],
                "dob": updated_user["dob"].isoformat(),
                "isOnboardingComplete": updated_user["is_onboarding_complete"],
                "mobile": updated_user["mobile"],
                "parentMobile": updated_user["parent_mobile"],
                "userType": updated_user["user_type"],
                "schoolOrCollege": updated_user["school_or_college"],
                "schoolName": updated_user["school_name"],
                "collegeName": updated_user["college_name"],
                "course": updated_user["course"],
                "class": updated_user["class"],
                "board": updated_user["board"],
                "stateBoard": updated_user["state_board"],
                "stream": updated_user["stream"],
                "subStream": updated_user["sub_stream"],
                "goal": updated_user["goal"],
                "childUsername": updated_user["child_username"],
                "avatar": updated_user["avatar"],
                "notificationsEnabled": updated_user["notifications_enabled"],
                "createdAt": updated_user["created_at"].isoformat(),
                "updatedAt": updated_user["updated_at"].isoformat(),
                "lastLogin": updated_user["last_login"].isoformat() if updated_user["last_login"] else None,
                "isActive": updated_user["is_active"]
            }
        }
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@app.get("/api/users/me")
async def get_profile(db=Depends(get_db), current_user=Depends(get_current_user)):
    return {"user": {
        "id": current_user["id"],
        "firstName": current_user["first_name"],
        "middleName": current_user["middle_name"],
        "lastName": current_user["last_name"],
        "email": current_user["email"],
        "dob": current_user["dob"].isoformat(),
        "isOnboardingComplete": current_user["is_onboarding_complete"],
        "mobile": current_user["mobile"],
        "parentMobile": current_user["parent_mobile"],
        "userType": current_user["user_type"],
        "schoolOrCollege": current_user["school_or_college"],
        "schoolName": current_user["school_name"],
        "collegeName": current_user["college_name"],
        "course": current_user["course"],
        "class": current_user["class"],
        "board": current_user["board"],
        "stateBoard": current_user["state_board"],
        "stream": current_user["stream"],
        "subStream": current_user["sub_stream"],
        "goal": current_user["goal"],
        "childUsername": current_user["child_username"],
        "avatar": current_user["avatar"],
        "notificationsEnabled": current_user["notifications_enabled"],
        "createdAt": current_user["created_at"].isoformat(),
        "updatedAt": current_user["updated_at"].isoformat(),
        "lastLogin": current_user["last_login"].isoformat() if current_user["last_login"] else None,
        "isActive": current_user["is_active"]
    }}

@app.get("/api/institute/me")
async def get_institute_profile(db=Depends(get_db), current_institute=Depends(get_current_institute)):
    return {"institute": {
        "id": current_institute["id"],
        "name": current_institute["name"],
        "email": current_institute["email"],
        "address": current_institute["address"],
        "contact": current_institute["contact"],
        "website": current_institute["website"],
        "logo": current_institute["logo"],
        "description": current_institute["description"],
        "established_year": current_institute["established_year"],
        "affiliations": current_institute["affiliations"],
        "courses_offered": current_institute["courses_offered"]
    }}

@app.get("/api/colleges")
async def get_colleges(db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        educational_data = load_educational_data()
        colleges = [sanitize_college_name(college) for college in educational_data["colleges"].keys()]
        return {"colleges": colleges}
    except Exception as e:
        logger.error(f"Error fetching colleges: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching colleges: {str(e)}")

@app.get("/api/courses/{college_name}")
async def get_courses(college_name: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        sanitized_name = sanitize_college_name(college_name)
        educational_data = load_educational_data()
        courses = educational_data["colleges"].get(sanitized_name, [])
        return {"courses": courses}
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching courses: {str(e)}")

@app.post("/api/colleges/add")
async def add_college(college: CollegeAdd, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        sanitized_name = sanitize_college_name(college.collegeName)
        educational_data = load_educational_data()
        if sanitized_name not in educational_data["colleges"]:
            educational_data["colleges"][sanitized_name] = []
        if college.course and college.course not in educational_data["colleges"][sanitized_name]:
            educational_data["colleges"][sanitized_name].append(college.course)
        with open('educational_data.json', 'w') as f:
            json.dump(educational_data, f, indent=2)
        return {"message": "College and/or course added successfully"}
    except Exception as e:
        logger.error(f"Error adding college/course: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding college/course: {str(e)}")

@app.get("/api/boards")
async def get_boards(class_name: Optional[str] = None, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        state_boards = load_state_boards()
        if class_name in ['11', '12']:
            boards = [board["board_name"] for board in state_boards["higher_secondary_boards"]]
        else:
            boards = [board["board_name"] for board in state_boards["secondary_boards"]]
        return {"boards": boards}
    except Exception as e:
        logger.error(f"Error fetching boards: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching boards: {str(e)}")

@app.get("/api/state-boards")
async def get_state_boards(class_name: Optional[str] = None, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        state_boards = load_state_boards()
        if class_name in ['11', '12']:
            boards = [board["board_name"] for board in state_boards["higher_secondary_boards"]]
        else:
            boards = [board["board_name"] for board in state_boards["secondary_boards"]]
        return {"stateBoards": boards}
    except Exception as e:
        logger.error(f"Error fetching state boards: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching state boards: {str(e)}")




@app.get("/api/subjects/{board}/{class_num}")
async def get_subjects(board: str, class_num: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        # Load subjects from JSON file
        subject_cache = load_subject_cache()
        key = f"{board}_{class_num}"
        subjects = subject_cache.get(key, [])
        if not subjects:
            # Fallback to OpenAI if not found in JSON
            subjects = get_subjects_from_openai(board, class_num)
            if not subjects:
                raise HTTPException(status_code=404, detail="No subjects found for the specified board and class")
            # Optionally, update the JSON file with new data
            subject_cache[key] = subjects
            with open('subject_cache.json', 'w') as f:
                json.dump(subject_cache, f, indent=2)
        return {"subjects": subjects}
    except Exception as e:
        logger.error(f"Error fetching subjects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching subjects: {str(e)}")


@app.get("/api/syllabus/{board}/{class_num}/{subject}")
async def get_syllabus(board: str, class_num: int, subject: str, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        # Check if syllabus exists in cache
        cached = await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            board, class_num, subject
        )
        if cached and cached["syllabus_data"]:
            try:
                syllabus = json.loads(cached["syllabus_data"])
                logger.info(f"Returning cached syllabus for {board} Class {class_num} {subject}")
                return {"syllabus": syllabus}
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing cached syllabus data: {str(e)}")
                # Proceed to fetch from OpenAI if cached data is invalid

        # Fetch from OpenAI if not cached or cache is invalid
        syllabus = get_syllabus_from_openai(board, class_num, subject)
        
        # Cache the response, even if empty
        try:
            await db.execute(
                """
                INSERT INTO syllabus_cache (board, class_num, subject, syllabus_data)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (board, class_num, subject)
                DO UPDATE SET syllabus_data = EXCLUDED.syllabus_data, updated_at = CURRENT_TIMESTAMP
                """,
                board, class_num, subject, json.dumps(syllabus)
            )
            logger.info(f"Cached syllabus for {board} Class {class_num} {subject}, chapters: {len(syllabus.get('chapters', []))}")
        except asyncpg.exceptions.DataError as e:
            logger.error(f"Database error while caching syllabus: {str(e)}")
            # Continue to return syllabus even if caching fails
        
        return {"syllabus": syllabus}
    except asyncpg.exceptions.UndefinedTableError:
        logger.error("Table syllabus_cache does not exist")
        raise HTTPException(status_code=500, detail="Syllabus cache table is not set up in the database")
    except Exception as e:
        logger.error(f"Error getting syllabus: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting syllabus: {str(e)}")


@app.post("/api/study-plan/generate")
async def generate_study_plan(plan_request: StudyPlanRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        # Fetch syllabus from cache
        cached_syllabus = await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            current_user["board"] or "CBSE",  # Fallback to CBSE if board not set
            int(current_user["class"] or 10),  # Fallback to class 10
            plan_request.subject
        )
        if not cached_syllabus:
            raise HTTPException(status_code=404, detail="Syllabus not found")

        syllabus = json.loads(cached_syllabus["syllabus_data"])
        chapters = syllabus.get("chapters", [])

        # Filter chapters to include only weak chapters (or all if none specified)
        target_chapters = [
            chapter for chapter in chapters
            if not plan_request.weakChapters or chapter["name"] in plan_request.weakChapters
        ]
        if not target_chapters:
            raise HTTPException(status_code=400, detail="No matching chapters found for the study plan")

        # Generate dynamic study plan
        study_plan = {}
        start_date = datetime.now().date()
        for week in range(1, 3):  # Plan for 2 weeks
            week_key = f"Week {week}"
            study_plan[week_key] = []
            for chapter in target_chapters[:2]:  # Limit to 2 chapters per week
                for topic in chapter.get("topics", [])[:2]:  # Limit to 2 topics per chapter
                    study_plan[week_key].append({
                        "date": (start_date + timedelta(days=(week-1)*7)).isoformat(),
                        "chapter": chapter["name"],
                        "topic": topic["name"],
                        "subtopic": topic["subtopics"][0] if topic.get("subtopics") else "",
                        "time": 2.0,  # Default study time
                        "completed": False
                    })

        # Store the plan in the database
        await db.execute(
            "INSERT INTO study_plan (user_id, subject, plan_data, weak_chapters) VALUES ($1, $2, $3, $4)",
            user_id, plan_request.subject, study_plan, plan_request.weakChapters
        )
        logger.info(f"Generated study plan for user {user_id}, subject {plan_request.subject}")
        return {"studyPlan": study_plan}
    except asyncpg.exceptions.UndefinedTableError:
        logger.error("Table study_plan does not exist")
        raise HTTPException(status_code=500, detail="Study plan table is not set up in the database")
    except Exception as e:
        logger.error(f"Failed to generate study plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {str(e)}")


@app.post("/api/syllabus/regenerate/{board}/{class_num}/{subject}")
async def regenerate_syllabus(
    board: str,
    class_num: int,
    subject: str,
    missing_chapters: Optional[str] = None, 
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # Clear existing cache entry
        await db.execute(
            "DELETE FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            board, class_num, subject
        )
        logger.info(f"Cleared syllabus cache for {board} Class {class_num} {subject}")

        # Fetch fresh syllabus from OpenAI
        syllabus = get_syllabus_from_openai(board, class_num, subject, missing_chapters)

        # Cache the new response, even if empty
        try:
            await db.execute(
                """
                INSERT INTO syllabus_cache (board, class_num, subject, syllabus_data)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (board, class_num, subject)
                DO UPDATE SET syllabus_data = EXCLUDED.syllabus_data, updated_at = CURRENT_TIMESTAMP
                """,
                board, class_num, subject, json.dumps(syllabus)
            )
            logger.info(f"Cached fresh syllabus for {board} Class {class_num} {subject}, chapters: {len(syllabus.get('chapters', []))}")
        except asyncpg.exceptions.DataError as e:
            logger.error(f"Database error while caching syllabus: {str(e)}")
            # Continue to return syllabus even if caching fails

        return {"syllabus": syllabus}
    except asyncpg.exceptions.UndefinedTableError:
        logger.error("Table syllabus_cache does not exist")
        raise HTTPException(status_code=500, detail="Syllabus cache table is not set up in the database")
    except Exception as e:
        logger.error(f"Error regenerating syllabus: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error regenerating syllabus: {str(e)}")

@app.post("/api/tutor/explain")
async def explain_topic(explain_request: ExplainRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        explanation = explain_topic_with_openai(explain_request.board, explain_request.classNum, explain_request.subject, explain_request.chapter, explain_request.topic)
        return {"explanation": explanation, "image": None}
    except Exception as e:
        logger.error(f"Failed to explain topic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to explain topic: {str(e)}")

@app.get("/api/institute/performance")
async def get_institute_performance(db=Depends(get_db), current_institute=Depends(get_current_institute)):
    institute_id = current_institute["id"]
    performance = {
        "student_count": await db.fetchval(
            "SELECT COUNT(*) FROM user_institute_mapping m JOIN users u ON m.user_id = u.id WHERE m.institute_id = $1 AND u.user_type = 'student'",
            institute_id
        ),
        "teacher_count": await db.fetchval(
            "SELECT COUNT(*) FROM user_institute_mapping m JOIN users u ON m.user_id = u.id WHERE m.institute_id = $1 AND u.user_type = 'teacher'",
            institute_id
        ),
        "avg_performance_score": await db.fetchval(
            "SELECT AVG(performance_score) FROM performance WHERE institute_id = $1 AND user_type = 'student'",
            institute_id
        ) or 0.0,
        "section_wise": await db.fetch(
            "SELECT section, AVG(performance_score) as avg_score FROM performance WHERE institute_id = $1 AND user_type = 'student' GROUP BY section",
            institute_id
        ),
        "class_wise": await db.fetch(
            "SELECT class, AVG(performance_score) as avg_score FROM performance WHERE institute_id = $1 AND user_type = 'student' GROUP BY class",
            institute_id
        ),
        "individual_students": await db.fetch(
            "SELECT u.first_name, u.last_name, p.performance_score FROM users u JOIN performance p ON u.id = p.user_id WHERE p.institute_id = $1 AND u.user_type = 'student'",
            institute_id
        )
    }
    return performance


@app.get("/api/progress")
async def get_progress(subject: Optional[str] = None, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        query = """
        SELECT subject, overall_score, progress, completed_topics, total_topics, 
               mock_tests_taken, total_mock_tests, study_hours, percentile, 
               weak_areas, last_activity, trend
        FROM subject_performances
        WHERE user_id = $1
        """
        params = [user_id]
        
        if subject:
            query += " AND subject = $2"
            params.append(subject)

        performances = await db.fetch(query, *params)
        
        # Convert database rows to the expected response format
        response = [{
            "subject": row["subject"],
            "overallScore": row["overall_score"],
            "progress": row["progress"],
            "completedTopics": row["completed_topics"],
            "totalTopics": row["total_topics"],
            "mockTestsTaken": row["mock_tests_taken"],
            "totalMockTests": row["total_mock_tests"],
            "studyHours": row["study_hours"],
            "percentile": row["percentile"],
            "weakAreas": row["weak_areas"],
            "lastActivity": row["last_activity"].isoformat() if row["last_activity"] else None,
            "trend": row["trend"]
        } for row in performances]
        
        return {"performances": response}
    except Exception as e:
        logger.error("Table subject_performances does not exist")
        raise HTTPException(status_code=500, detail="Progress tracking is not set up in the database")
    except Exception as e:
        logger.error(f"Error fetching progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching progress: {str(e)}")


@app.get("/api/progress/stats")
async def get_progress_stats(range: Optional[str] = None, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        # Fetch streak, XP, and badges from streaks table
        streak_data = await db.fetchrow(
            "SELECT streak, xp, badges FROM streaks WHERE user_id = $1",
            user_id
        )
        streak = streak_data["streak"] if streak_data else 0
        xp = streak_data["xp"] if streak_data else 0
        badges = streak_data["badges"] if streak_data and streak_data["badges"] else []

        # Fetch daily goals from daily_goals table
        goals_data = await db.fetch(
            "SELECT id, task, completed, xp FROM daily_goals WHERE user_id = $1",
            user_id
        )
        todays_goals = [{
            "id": row["id"],
            "task": row["task"],
            "completed": row["completed"],
            "xp": row["xp"]
        } for row in goals_data]

        # Fetch achievements from achievements table
        achievements_data = await db.fetch(
            "SELECT id, title, description, icon, xp, earned FROM achievements WHERE user_id = $1",
            user_id
        )
        todays_achievements = [{
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "icon": row["icon"],
            "xp": row["xp"],
            "earned": row["earned"]
        } for row in achievements_data]

        # Return response in the expected format
        return {
            "streak": streak,
            "xp": xp,
            "badges": badges,
            "todaysGoals": todays_goals,
            "todaysAchievements": todays_achievements
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return {
            "streak": 0,
            "xp": 0,
            "badges": [],
            "todaysGoals": [],
            "todaysAchievements": []
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
    
# Load educational data from JSON files
def load_educational_data():
    try:
        with open('educational_data.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading educational_data.json: {str(e)}")
        return {"colleges": {}, "stateBoards": []}

def load_state_boards():
    try:
        with open('state_boards.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading state_boards.json: {str(e)}")
        return {"secondary_boards": [], "higher_secondary_boards": []}

# Admin routes
@app.get("/api/admin/stats")
async def get_admin_stats(db=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    stats = {
        "students": await db.fetchval("SELECT COUNT(*) FROM users WHERE user_type = 'student'"),
        "teachers": await db.fetchval("SELECT COUNT(*) FROM users WHERE user_type = 'teacher'"),
        "parents": await db.fetchval("SELECT COUNT(*) FROM users WHERE user_type = 'parent'"),
        "schools": await db.fetchval("SELECT COUNT(DISTINCT school_name) FROM users WHERE school_name IS NOT NULL"),
        "connected_students": await db.fetchval("SELECT COUNT(*) FROM user_institute_mapping")
    }
    return stats

@app.post("/api/admin/institute")
async def create_institute(institute: InstituteCreate, db=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        institute_id = str(uuid.uuid4())
        token = secrets.token_hex(32)
        invite_link = f"https://your-app.com/invite/{invite_code}"
        hashed_password = pwd_context.hash(institute.password)
        await db.execute(
            """
            INSERT INTO institutes (
                id, name, password, invite_code, token, invite_link, address, contact, email, website,
                logo, description, established_year, affiliations, courses_offered
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
            institute_id, institute.name, hashed_password, invite_code, token, invite_link,
            institute.address, institute.contact, institute.email, institute.website,
            institute.logo, institute.description, institute.established_year,
            institute.affiliations, institute.courses_offered
        )
        logger.info(f"Created institute: {institute.name} with ID: {institute_id}")
        return {
            "institute_id": institute_id,
            "name": institute.name,
            "invite_code": invite_code,
            "invite_link": invite_link,
            "address": institute.address,
            "contact": institute.contact,
            "email": institute.email,
            "website": institute.website,
            "logo": institute.logo,
            "description": institute.description,
            "established_year": institute.established_year,
            "affiliations": institute.affiliations,
            "courses_offered": institute.courses_offered
        }
    except asyncpg.exceptions.UniqueViolationError:
        logger.warning(f"Invite code or token already exists for institute: {institute.name}")
        raise HTTPException(status_code=422, detail="Invite code or token already exists")
    except Exception as e:
        logger.error(f"Error creating institute: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create institute: {str(e)}")

@app.get("/api/admin/users", response_model=List[UserResponse])
async def get_users(db=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = await db.fetch("""
        SELECT u.id, u.first_name, u.last_name, u.email, u.user_type, u.school_name, u.college_name,
               m.institute_id, u.company
        FROM users u
        LEFT JOIN user_institute_mapping m ON u.id = m.user_id
    """)
    return users

@app.get("/api/admin/institutes", response_model=List[InstituteResponse])
async def get_institutes(db=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    institutes = await db.fetch("""
        SELECT i.id, i.name,
               (SELECT COUNT(*) FROM user_institute_mapping m JOIN users u ON m.user_id = u.id
                WHERE m.institute_id = i.id AND u.user_type = 'student') as student_count,
               (SELECT COUNT(*) FROM user_institute_mapping m JOIN users u ON m.user_id = u.id
                WHERE m.institute_id = i.id AND u.user_type = 'teacher') as teacher_count
        FROM institutes i
    """)
    return institutes


@app.get("/api/resources")
async def get_resources(db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        user_grade = current_user["class"]
        if not user_grade:
            raise HTTPException(status_code=400, detail="User grade not specified")
        
        # Query resources from the database filtered by user's grade
        resources = await db.fetch(
            "SELECT id, title, description, type, subject, grade, duration, level, url, thumbnail "
            "FROM resources WHERE grade = $1 OR grade = 'all'",
            user_grade
        )
        
        # Convert database rows to Resource model
        response = [{
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "type": row["type"],
            "subject": row["subject"],
            "grade": row["grade"],
            "duration": row["duration"],
            "level": row["level"],
            "url": row["url"],
            "thumbnail": row["thumbnail"]
        } for row in resources]
        
        return {"resources": response}
    except Exception as e:
        logger.error(f"Error fetching resources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching resources: {str(e)}")


@app.post("/api/tutor/chat")
async def chat_with_tutor(chat_request: ChatRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        board = chat_request.board or current_user["board"] or "CBSE"
        class_num = chat_request.class_num or int(current_user["class"] or 10)
        subject = chat_request.subject or "Mathematics"

        # Store user message
        await db.execute(
            "INSERT INTO chat_history (user_id, role, message, subject, board, class_num) VALUES ($1, $2, $3, $4, $5, $6)",
            user_id, "user", chat_request.message, subject, board, class_num
        )

        # Generate response using OpenAI
        prompt = f"""
        {SYSTEM_PROMPT}
        The student has asked: '{chat_request.message}' for {board} Class {class_num} {subject}.
        Provide a detailed response following the four-part structure:
        1. Start with a detailed, engaging real-life example that illustrates the concept.
        2. Provide the textbook definition or explanation, including any formulas or key notes.
        3. Include a detailed additional example aligned with the textbook style.
        4. End with an understanding check: "Does this make sense, or should I explain it another way?" followed by a short, syllabus-based quiz question.
        If the question is not specific to a topic or is outside the syllabus, provide a general response encouraging the student to ask a syllabus-related question.
        Return only the response text, without any Markdown or code block formatting.
        """
        response = openai.ChatCompletion.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1000
        )
        ai_response = response.choices[0].message.content.strip()

        # Store AI response
        await db.execute(
            "INSERT INTO chat_history (user_id, role, message, subject, board, class_num) VALUES ($1, $2, $3, $4, $5, $6)",
            user_id, "assistant", ai_response, subject, board, class_num
        )

        return {"response": ai_response}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


# Get chat history endpoint
@app.get("/api/tutor/chat/history")
async def get_chat_history(db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        messages = await db.fetch(
            """
            SELECT id, role, message, subject, board, class_num, timestamp, liked
            FROM chat_history
            WHERE user_id = $1
            ORDER BY timestamp ASC
            """,
            user_id
        )
        return {
            "messages": [
                {
                    "id": msg["id"],
                    "role": msg["role"],
                    "message": msg["message"],
                    "subject": msg["subject"],
                    "board": msg["board"],
                    "class_num": msg["class_num"],
                    "timestamp": msg["timestamp"].isoformat(),
                    "liked": msg["liked"]
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching chat history: {str(e)}")

# Update feedback endpoint
@app.post("/api/tutor/feedback")
async def update_feedback(feedback: FeedbackRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        # Verify the message belongs to the user
        message = await db.fetchrow(
            "SELECT user_id FROM chat_history WHERE id = $1",
            feedback.message_id
        )
        if not message or message["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to update this message")
        
        await db.execute(
            "UPDATE chat_history SET liked = $1 WHERE id = $2",
            feedback.liked, feedback.message_id
        )
        return {"message": "Feedback updated successfully"}
    except Exception as e:
        logger.error(f"Error updating feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating feedback: {str(e)}")


@app.post("/api/previous-marks")
async def store_previous_marks(
    marks_request: PreviousMarksRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        user_id = current_user["id"]
        marks_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO previous_marks (id, user_id, subject, last_exam, last_test, assignment, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            marks_id, user_id, marks_request.subject, marks_request.lastExam,
            marks_request.lastTest, marks_request.assignment, datetime.utcnow()
        )
        logger.info(f"Stored previous marks for user {user_id}, subject {marks_request.subject}")
        return {"message": "Previous marks stored successfully", "marksId": marks_id}
    except Exception as e:
        logger.error(f"Failed to store previous marks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store previous marks: {str(e)}")


@app.post("/api/quiz/generate")
async def generate_quiz(quiz_request: QuizGenerateRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        # Compute difficulty based on previousMarks
        previous_marks = quiz_request.previousMarks
        if previous_marks < 50:
            difficulty = "beginner"
        elif previous_marks <= 75:
            difficulty = "intermediate"
        else:
            difficulty = "advanced"

        # Fetch syllabus from cache
        cached_syllabus = await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            quiz_request.board, int(quiz_request.currentClass), quiz_request.subject
        )
        if not cached_syllabus:
            logger.error(f"Syllabus not found for {quiz_request.board} Class {quiz_request.currentClass} {quiz_request.subject}")
            raise HTTPException(status_code=404, detail="Syllabus not found for current class")

        # Ensure syllabus_data is a dictionary
        syllabus_data = cached_syllabus["syllabus_data"]
        if isinstance(syllabus_data, str):
            try:
                syllabus_data = json.loads(syllabus_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing syllabus_data: {str(e)}")
                raise HTTPException(status_code=500, detail="Invalid syllabus data in cache")

        # Extract chapters from syllabus_data
        syllabus_chapters = [chapter["name"] for chapter in syllabus_data.get("chapters", [])]
        valid_chapters = [chapter for chapter in quiz_request.chapters if chapter in syllabus_chapters]
        if not valid_chapters:
            logger.error(f"No valid chapters provided for quiz generation: {quiz_request.chapters}")
            raise HTTPException(status_code=400, detail="No valid chapters provided for quiz generation")

        # Generate quiz
        quiz = create_quiz_from_openai(
            quiz_request.board, int(quiz_request.currentClass), quiz_request.subject, valid_chapters, difficulty
        )
        if not quiz:
            logger.error("Quiz generation returned empty quiz")
            raise HTTPException(status_code=500, detail="Failed to generate quiz: No questions generated")

        # Store quiz in database
        user_id = current_user["id"]
        quiz_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO quizzes (id, user_id, subject, board, class, difficulty, questions, created_at, goal)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            quiz_id, user_id, quiz_request.subject, quiz_request.board, quiz_request.currentClass,
            difficulty, json.dumps(quiz), datetime.utcnow(), quiz_request.goal
        )
        
        logger.info(f"Generated quiz for user {user_id}, subject {quiz_request.subject}, quizId {quiz_id}")
        return {"quiz": {"subject": quiz_request.subject, "questions": quiz}, "quizId": quiz_id}
    except Exception as e:
        logger.error(f"Failed to generate quiz: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

@app.post("/api/quiz/submit")
async def submit_quiz_results(quiz_results: QuizResultsRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        quiz_id = str(uuid.uuid4())
        score = sum(1 for result in quiz_results.results.values() if result)
        total_questions = len(quiz_results.results)
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0

        await db.execute(
            """
            INSERT INTO quiz_results (id, user_id, quiz_type, score, total_questions, percentage, results, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            quiz_id, user_id, quiz_results.quizType, score, total_questions, percentage,
            json.dumps(quiz_results.results), datetime.utcnow()
        )

        return {
            "message": "Quiz results submitted successfully",
            "score": score,
            "total_questions": total_questions,  # Added to match frontend expectation
            "percentage": percentage,
            "quizId": quiz_id
        }
    except Exception as e:
        logger.error(f"Error submitting quiz results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting quiz results: {str(e)}")


@app.post("/api/quiz/results")
async def submit_quiz_results(
    request: QuizResultsRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        user_id = current_user["id"]
        quiz_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO quiz_results (id, user_id, quiz_type, results, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            quiz_id, user_id, request.quizType, json.dumps(request.results), datetime.utcnow()
        )
        logger.info(f"Quiz results submitted for user {user_id}, quiz type {request.quizType}")
        return {"message": "Quiz results submitted successfully", "quizId": quiz_id}
    except asyncpg.exceptions.UndefinedTableError:
        logger.error("Table quiz_results does not exist")
        raise HTTPException(status_code=500, detail="Quiz results table is not set up in the database")
    except Exception as e:
        logger.error(f"Failed to submit quiz results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit quiz results: {str(e)}")



@app.post("/api/study-plan")
async def create_study_plan(plan_request: StudyPlanRequest, db=Depends(get_db), current_user=Depends(get_current_user)):
    try:
        user_id = int(current_user["id"])
        logger.info(f"user_id type: {type(user_id)}, value: {user_id}")

        # Fetch syllabus from cache
        cached_syllabus = await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            current_user["board"] or "CBSE", int(current_user["class"] or 10), plan_request.subject
        )
        if not cached_syllabus:
            logger.error(f"Syllabus not found for {current_user['board'] or 'CBSE'} Class {current_user['class'] or 10} {plan_request.subject}")
            raise HTTPException(status_code=404, detail="Syllabus not found")

        syllabus_data = cached_syllabus["syllabus_data"]
        if isinstance(syllabus_data, str):
            try:
                syllabus = json.loads(syllabus_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing syllabus_data: {str(e)}")
                raise HTTPException(status_code=500, detail="Invalid syllabus data in cache")
        else:
            syllabus = syllabus_data

        chapters = syllabus.get("chapters", [])
        if not chapters:
            logger.error(f"No chapters found for subject {plan_request.subject}")
            raise HTTPException(status_code=400, detail="No chapters found for the study plan")

        # Separate weak and non-weak chapters
        weak_chapters = plan_request.weakChapters or []
        weak_chapter_list = [chapter for chapter in chapters if chapter["name"] in weak_chapters]
        other_chapters = [chapter for chapter in chapters if chapter["name"] not in weak_chapters]
        prioritized_chapters = weak_chapter_list + other_chapters  # Weak chapters come first

        if not prioritized_chapters:
            logger.error(f"No matching chapters found for subject {plan_request.subject}")
            raise HTTPException(status_code=400, detail="No matching chapters found for the study plan")

        # Calculate number of weeks needed (e.g., 2-3 chapters per week)
        chapters_per_week = 2
        total_weeks = max(1, (len(prioritized_chapters) + chapters_per_week - 1) // chapters_per_week)

        # Generate dynamic study plan
        study_plan_data = {}
        start_date = datetime.now().date()
        for week in range(1, total_weeks + 1):
            week_key = f"Week {week}"
            study_plan_data[week_key] = []
            # Select chapters for this week (up to chapters_per_week)
            week_chapters = prioritized_chapters[(week-1)*chapters_per_week : week*chapters_per_week]
            for chapter in week_chapters:
                is_weak = chapter["name"] in weak_chapters
                study_time = 3.0 if is_weak else 2.0  # More time for weak chapters
                for topic in chapter.get("topics", [])[:2]:  # Limit to 2 topics per chapter
                    study_plan_data[week_key].append({
                        "date": (start_date + timedelta(days=(week-1)*7)).isoformat(),
                        "chapter": chapter["name"],
                        "topic": topic["name"],
                        "subtopic": topic["subtopics"][0] if topic.get("subtopics") else "",
                        "time": study_time,
                        "completed": False
                    })

        # Validate study_plan_data
        if not study_plan_data or not any(study_plan_data.values()):
            logger.error("Generated study plan is empty")
            raise HTTPException(status_code=500, detail="Failed to generate study plan: Empty plan data")

        plan_id = uuid.uuid4()
        created_at = datetime.utcnow()

        # Store the plan in the database
        await db.execute(
            """
            INSERT INTO study_plan (id, user_id, subject, plan_data, weak_chapters, plan_type, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            plan_id, user_id, plan_request.subject, json.dumps(study_plan_data), 
            plan_request.weakChapters, plan_request.planType, created_at
        )

        response = {
            "studyPlan": {
                "id": str(plan_id),
                "userId": user_id,
                "subject": plan_request.subject,
                "planData": study_plan_data,
                "weakChapters": plan_request.weakChapters or [],
                "planType": plan_request.planType,
                "createdAt": created_at.isoformat()
            }
        }

        logger.info(f"Generated study plan response: {json.dumps(response, indent=2)}")
        logger.info(f"Generated study plan for user {user_id}, subject {plan_request.subject}, planType {plan_request.planType}")

        return response
    except asyncpg.exceptions.UndefinedTableError:
        logger.error("Table study_plan does not exist")
        raise HTTPException(status_code=500, detail="Study plan table is not set up in the database")
    except Exception as e:
        logger.error(f"Failed to generate study plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate study plan: {str(e)}")
    

@app.post("/api/study-plan/create")
async def create_study_plan(data: dict, db=Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        user_id = 1  # Replace with actual user ID from token
        quiz_results = data.get("quizResults", {})
        wrong_topics = [q["id"] for q, result in quiz_results.items() if not result]
        subjects = [{"subject": data["subject"], "chapter": c["name"], "topics": c["topics"]} for c in (await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            data["board"], int(data["currentClass"]), data["subject"]
        ))["syllabus_data"]["chapters"]] if (await db.fetchrow(
            "SELECT syllabus_data FROM syllabus_cache WHERE board = $1 AND class_num = $2 AND subject = $3",
            data["board"], int(data["currentClass"]), data["subject"]
        )) else []
        study_plan = generate_study_plan(subjects, wrong_topics)

        plan_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO study_plan (id, user_id, subject, plan_data, weak_chapters, plan_type, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            plan_id, user_id, data["subject"], json.dumps(study_plan), json.dumps(wrong_topics), data["planType"], datetime.utcnow()
        )

        return {"planId": plan_id, "plan": study_plan}
    except Exception as e:
        logger.error(f"Study plan creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create study plan")
  

