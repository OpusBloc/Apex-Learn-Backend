import streamlit as st
import os
import datetime
from openai import OpenAI
from dotenv import load_dotenv
import json
import uuid
from pathlib import Path
import pandas as pd
import plotly.express as px 
from collections import defaultdict

# --- Configuration & Setup ---
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

# Simple file-based database setup
DB_DIR = Path("app_data")
DB_DIR.mkdir(exist_ok=True)
WORKSHEETS_DB = DB_DIR / "worksheets.db.json"
SUBMISSIONS_DB = DB_DIR / "submissions.db.json"

CLASS_ROSTER_DB = DB_DIR / "class_roster.db.json"
ASSIGNMENTS_DB = DB_DIR / "assignments.db.json"

def load_db(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_db(data: dict, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# ==============================================================================
# AI Teacher Assistant Class (Upgraded)
# ==============================================================================

class AITeacherAssistant:
    def __init__(self, model="gpt-4.1-nano"):
        if not API_KEY:
            raise ValueError("OPENAI_API_KEY not found.")
        self.client = OpenAI(api_key=API_KEY)
        self.model = model

    # Add this new method inside the AITeacherAssistant class
    def generate_performance_overview(self, student_name: str, topic: str, all_feedback: list) -> str:
        """
        Analyzes a student's incorrect answers and generates a motivational overview.
        """
        # if not incorrect_answers:
        #     return "" # No overview needed if everything is correct

        system_prompt = (
            "You are a kind, patient, and motivational AI tutor. Your goal is to provide encouraging "
            "feedback to a student based on their worksheet performance. Address the student by name. "
            "Start with positive reinforcement, gently explain the concepts behind the mistakes, and "
            "If solution base question then provide its solution like in maths, and for other subjects you can provide detailed explanation"
            "end with an encouraging closing statement."
        )
    
        # Format the incorrect answers for the prompt
        feedback_summary = "\n".join([
            f"- For question '{item['question']}', the feedback was: '{item['feedback']}'"
            for item in all_feedback
        ])

        user_prompt = (
            f"Please write a friendly and motivational performance overview for a student named {student_name}.\n"
            f"The worksheet topic was: {topic}.\n"
            f"Here are the questions they answered incorrectly:\n{feedback_summary}\n\n"
            f"Please explain the core concepts behind the correct answers in a simple and patient way. "
            f"Keep the entire overview concise and encouraging."
            f"Synthesize this into a cohesive summary. Acknowledge their effort, praise what they did well, and gently point out any patterns in their mistakes (e.g., spelling, specific concepts). Keep it encouraging."
        )
    
        # Use a direct text-based generation for this narrative response
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        )
        return response.choices[0].message.content.strip()

    def _get_json_response(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            st.error(f"An API or JSON parsing error occurred: {e}")
            return {}

    def generate_mixed_worksheet(self, standard: str, board: str, subject: str, topic: str, difficulty: str, num_questions: int) -> dict:
        """
        Generates a worksheet with a mix of question types and a structured answer key.
        """
        system_prompt = (
            "You are an expert curriculum designer for the Indian education system. "
            "Your task is to generate a well-structured worksheet in JSON format. The root of the JSON object must be a key 'worksheet' which contains a list of question objects. "
            "Each question object must have three keys: 'type' (can be 'mcq', 'fill_in_the_blank', or 'short_answer'), 'question' (the question text), and 'answer' (the correct answer). "
            "The questions should me based on users standard and specific chosen board syllabus to the defined topic"
            "Do not generate questions out of users syllabus."
            "For 'mcq' questions, you must also include an 'options' key, which is a list of 4 strings. "
            "For 'fill_in_the_blank' questions, use '____' to indicate the blank."
        )
        user_prompt = (
            f"Please generate a worksheet with a total of {num_questions} questions for a student in **Class {standard}** of the **{board}** board, studying **{subject}**.\n"
            f"The specific topic is **'{topic}'**.\n"
            f"The difficulty level should be **{difficulty}**.\n"
            f"The questions should be a mix of Multiple Choice (MCQs), Fill-in-the-blanks, and Short Answer questions. "
            f"Ensure the generated content is a single, valid JSON object."
        )
        return self._get_json_response(system_prompt, user_prompt)

    # The adaptive test generator from the previous script can remain here if needed
    def generate_adaptive_worksheet(self, standard: str, board: str, subject: str, topic: str, difficulty: str, num_questions: int, performance_summary: str) -> dict:
        """
        Generates an adaptive worksheet based on student's past performance, with a mix of question types and a structured answer key.
        """
        system_prompt = (
            "You are an expert curriculum designer for the Indian education system. "
            "Your task is to generate a well-structured worksheet in JSON format. The root of the JSON object must be a key 'worksheet' which contains a list of question objects. "
            "Each question object must have three keys: 'type' (can be 'mcq', 'fill_in_the_blank', or 'short_answer'), 'question' (the question text), and 'answer' (the correct answer). "
            "The questions should be based on user's standard and specific chosen board syllabus to the defined topic. "
            "Do not generate questions out of user's syllabus. "
            "For 'mcq' questions, you must also include an 'options' key, which is a list of 4 strings. "
            "For 'fill_in_the_blank' questions, use '____' to indicate the blank."
        )
        user_prompt = (
            f"Please generate an adaptive worksheet with a total of {num_questions} questions for a student in **Class {standard}** of the **{board}** board, studying **{subject}**.\n"
            f"The specific topic is **'{topic}'**.\n"
            f"The difficulty level should be **{difficulty}**.\n"
            f"The questions should be a mix of Multiple Choice (MCQs), Fill-in-the-blanks, and Short Answer questions. "
            f"Adapt the questions based on the student's past performance, focusing on areas of weakness where relevant:\n{performance_summary}\n"
            f"Ensure the generated content is a single, valid JSON object."
        )
        return self._get_json_response(system_prompt, user_prompt)
    
    def get_semantic_grade_and_feedback(self, question: str, student_answer: str, correct_answer: str) -> dict:
        """
        Uses the LLM to grade a single answer based on semantic similarity.
        Returns True if the answer is correct, False otherwise.
        """
        system_prompt = (
            "You are a strict but fair grading assistant. Evaluate if a student's answer is semantically correct. "
            "If the core concept is wrong (e.g., 'Pythagoras' instead of 'hypotenuse'), it is 'Incorrect'. "
            "If the answer is correct but has minor issues (like spelling), grade it as 'Correct' but mention the issue in the feedback. "
            "Your response MUST be a JSON object with two keys: 'grade' (a single word: 'Correct' or 'Incorrect') and 'feedback' (a single, concise sentence of feedback)."
        )
        user_prompt = (
            f"Evaluate this answer:\n\n"
            f"Question: \"{question}\"\n"
            f"Student's Answer: \"{student_answer}\"\n"
            f"Model Correct Answer: \"{correct_answer}\"\n\n"
            f"Is the student's core answer semantically correct? Provide your response in the specified JSON format."
        )
        return self._get_json_response(system_prompt, user_prompt)
    

    # Add this new method inside the AITeacherAssistant class
    def validate_topic_for_subject(self, standard: str, board: str, subject: str, topic: str) -> bool:
        """
        Uses the LLM to quickly validate if a topic is relevant for a given subject.
        Returns True if valid, False otherwise.
        """
        system_prompt = (
            "You are a validation assistant for an educational app. Your job is to check if a topic is relevant to a subject "
            "for a specific grade and board in the Indian education system. Your response MUST be a single word: either 'Valid' or 'Invalid'."
        )
        user_prompt = (
            f"For a student in **Class {standard}** of the **{board}** board, is the topic **'{topic}'** a valid and relevant part of the **'{subject}'** curriculum? Respond with only 'Valid' or 'Invalid'."
            f"For example, 'Photosynthesis' is 'Valid' for 'Science', but 'Triangles' is 'Invalid' for 'Science'. "
            f"Respond with only 'Valid' or 'Invalid'."
        )
    
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0,
            )
            ai_verdict = response.choices[0].message.content.strip()
            # Stricter check for an exact match
            return ai_verdict.lower() == "valid"
        except Exception:
            return False
        
    # Add these two new methods inside the AITeacherAssistant class

    def generate_class_remediation_plan(self, topic: str, error_count: int, student_count: int) -> str:
        """
        Generates remediation suggestions for a topic the entire class is struggling with.
        """
        system_prompt = (
            "You are an expert educational strategist and AI curriculum advisor. Your task is to provide actionable, clear, and "
            "concise remediation suggestions for a teacher. Focus on practical steps a teacher can take to help students improve."
        )
        user_prompt = (
            f"A significant portion of my class is struggling with the topic: '{topic}'.\n"
            f"Specifically, {error_count} errors were recorded across {student_count} students on this topic.\n\n"
            "Please provide a bulleted list of 3-4 actionable remediation suggestions. These could include:\n"
            "- A suggestion for a focused review session.\n"
            "- An idea for a different type of activity (e.g., group work, visual aids).\n"
            "- A recommendation to generate a targeted practice worksheet on this specific topic.\n\n"
            "Keep the suggestions practical and easy for a teacher to implement."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        )
        return response.choices[0].message.content.strip()

    def generate_student_remediation_plan(self, student_name: str, performance_summary: str) -> str:
        """
        Generates a personalized remediation plan for an at-risk student.
        """
        system_prompt = (
            "You are a compassionate and insightful AI guidance counselor for students. Your goal is to create a personalized "
            "and encouraging remediation plan for a student who is struggling. Address the teacher, but frame the advice around "
            "helping the student. The tone should be supportive and constructive, not punitive."
        )
        user_prompt = (
            f"I'm concerned about a student named {student_name}. I need a personalized remediation plan.\n\n"
            f"Here is a summary of their recent performance:\n{performance_summary}\n\n"
            f"Please provide a short, actionable plan with 2-3 steps. The plan should include:\n"
            "1. A specific conceptual area to review with the student.\n"
            "2. A suggestion for a targeted activity or practice worksheet.\n"
            "3. An encouraging closing remark about building the student's confidence.\n\n"
            f"Focus on helping {student_name} get back on track."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        )
        return response.choices[0].message.content.strip()



# ==============================================================================
# Streamlit UI Views
# ==============================================================================

@st.cache_resource
def get_ai_assistant():
    return AITeacherAssistant()

# Helper function to avoid repeating the feedback display logic
def _display_feedback_results(feedback_data: dict):
    """Renders the feedback section for a student's submission."""
    ai_overview = feedback_data.get("ai_overview")
    incorrect_answers_report = feedback_data.get("feedback_report")

    if ai_overview:
        st.info(f"**💡 AI Tutor Overview:**\n\n{ai_overview}")

    if not incorrect_answers_report:
        st.success("🎉 **Excellent work! All your answers were correct!**")
    else:
        st.warning("Here are the corrections for the questions you missed:")
        for item in incorrect_answers_report:
            st.markdown("---")
            st.markdown(f"**Question:** {item['question']}")
            st.error(f"**Your Answer:** {item['your_answer']}")
            st.info(f"**Correct Answer:** {item['correct_answer']} \n\n*AI Feedback: {item['ai_feedback']}*")

# --- [REFACTORED] This is the new worksheet-taking view (Phase 3) ---
def render_worksheet_taker_view(assignment_id: str, student: dict, ai_assistant: AITeacherAssistant):
    """
    Renders the worksheet for a logged-in student for a specific assignment.
    This replaces the old link-based render_student_view.
    """
    st.title("✍️ Complete Your Assignment")
    
    # Load all DBs
    assignments = load_db(ASSIGNMENTS_DB)
    worksheets = load_db(WORKSHEETS_DB)
    submissions = load_db(SUBMISSIONS_DB)

    assignment = assignments.get(assignment_id)
    if not assignment:
        st.error("Assignment not found.")
        return

    worksheet_data = worksheets.get(assignment["worksheet_id"])
    if not worksheet_data:
        st.error("Worksheet data associated with this assignment is missing.")
        return

    st.header(f"Topic: {worksheet_data.get('topic', 'N/A')}")
    st.caption(f"Subject: {worksheet_data.get('subject')} | Due Date: {assignment.get('due_date')}")
    st.markdown("---")

    # Check for existing submission. This is the new re-submission prevention.
    existing_submission = None
    for sub_id, sub_data in submissions.items():
        if sub_data.get("assignment_id") == assignment_id and sub_data.get("student_id") == student["student_id"]:
            existing_submission = sub_data
            break

    # --- State 1: Worksheet has been submitted ---
    if existing_submission:
        st.success("✨ **You have already submitted this assignment!**")
        st.info("Your feedback is shown below.")
        
        _display_feedback_results({
            "ai_overview": existing_submission.get("ai_overview"),
            "feedback_report": existing_submission.get("feedback")
        })
        
        # Add a button to go back to the dashboard
        if st.button("← Back to Dashboard"):
            del st.session_state.viewing_assignment_id
            st.rerun()
        return

    # --- State 2: Worksheet NOT submitted yet. Log start time. ---
    if "assignment_start_time" not in st.session_state:
        st.session_state.assignment_start_time = pd.Timestamp.now().isoformat()

    worksheet_questions = worksheet_data.get("worksheet", [])

    with st.form("submission_form"):
        st.info(f"Welcome, {student['name']}! Please complete all questions and submit.")
        student_answers = {}
        
        for i, q in enumerate(worksheet_questions):
            q_key = f"q_{i}"
            if q['type'] == 'mcq':
                student_answers[q_key] = st.radio(f"**{i+1}. {q['question']}**", options=q['options'], index=None, key=q_key)
            elif q['type'] == 'fill_in_the_blank':
                student_answers[q_key] = st.text_input(f"**{i+1}. {q['question']}**", key=q_key)
            elif q['type'] == 'short_answer':
                student_answers[q_key] = st.text_area(f"**{i+1}. {q['question']}**", key=q_key)
        
        submitted = st.form_submit_button("Submit & Get Feedback")

    if submitted:
        with st.spinner("AI is carefully grading your answers... Hang tight!"):
            all_feedback_for_overview = []
            incorrect_answers_report = []
            total_questions = len(worksheet_questions)
            
            for i, q in enumerate(worksheet_questions):
                grade_result = ai_assistant.get_semantic_grade_and_feedback(
                    question=q['question'],
                    student_answer=str(student_answers.get(f"q_{i}", "")),
                    correct_answer=q['answer']
                )
                
                is_correct = grade_result.get("grade", "Incorrect").lower() == "correct"
                feedback_text = grade_result.get("feedback", "Could not evaluate.")
                all_feedback_for_overview.append({"question": q['question'], "feedback": feedback_text})
                
                if not is_correct:
                    incorrect_answers_report.append({
                        "question": q['question'],
                        "your_answer": str(student_answers.get(f"q_{i}", "")),
                        "correct_answer": q['answer'],
                        "ai_feedback": feedback_text
                    })

            ai_overview = ai_assistant.generate_performance_overview(
                student_name=student['name'], topic=worksheet_data['topic'], all_feedback=all_feedback_for_overview
            )
            
            incorrect_count = len(incorrect_answers_report)
            score_percent = ((total_questions - incorrect_count) / total_questions) * 100 if total_questions > 0 else 0
            
            # Save to new submission schema
            submission_id = str(uuid.uuid4())
            submissions[submission_id] = {
                "worksheet_id": assignment["worksheet_id"],
                "assignment_id": assignment_id,
                "student_id": student["student_id"],
                "student_name": student["name"], # Denormalize for easier reading in dashboard
                "topic": worksheet_data.get('topic'),
                "answers": student_answers,
                "feedback": incorrect_answers_report,
                "score_percent": score_percent,
                "ai_overview": ai_overview,
                "start_time": st.session_state.assignment_start_time,
                "submitted_at": pd.Timestamp.now().isoformat()
            }
            save_db(submissions, SUBMISSIONS_DB)

            # Clean up session state
            del st.session_state.assignment_start_time
            st.balloons()
            st.rerun() # This will rerun, hit the "existing_submission" block, and show feedback


# --- [NEW] Student Dashboard Function (Phase 3) ---
def render_student_dashboard(student_data: dict, class_id: str, ai_assistant: AITeacherAssistant):
    """
    This is the main dashboard for a logged-in student.
    It shows their assignments and allows them to take them.
    """
    
    # Check if student is currently taking a worksheet
    if "viewing_assignment_id" in st.session_state:
        render_worksheet_taker_view(st.session_state.viewing_assignment_id, student_data, ai_assistant)
        return

    # --- Main Dashboard View ---
    st.title(f"👋 Welcome, {student_data['name']}!")

    # Load DBs
    all_assignments = load_db(ASSIGNMENTS_DB)
    all_submissions = load_db(SUBMISSIONS_DB)

    # Filter assignments for this student's class
    my_class_assignments = {aid: data for aid, data in all_assignments.items() if data.get('class_id') == class_id}
    
    # Get all submission IDs for this student to quickly check completion
    my_submission_ids = set()
    for sub_id, sub_data in all_submissions.items():
        if sub_data.get("student_id") == student_data["student_id"]:
            my_submission_ids.add(sub_data.get("assignment_id"))

    todo_assignments = []
    completed_assignments = []

    for aid, adata in my_class_assignments.items():
        if aid in my_submission_ids:
            completed_assignments.append(adata)
        else:
            todo_assignments.append({"id": aid, **adata}) # Add the ID to the dict

    st.subheader("📬 To-Do Assignments")
    if not todo_assignments:
        st.info("Great job! You have no pending assignments.")
    else:
        for i, assign in enumerate(todo_assignments):
            with st.container(border=True):
                st.markdown(f"**Topic:** {assign.get('topic', 'N/A')}")
                st.caption(f"Assigned: {assign.get('assigned_date')} | Due: {assign.get('due_date')}")
                
                # Use a unique button key
                if st.button("Start Assignment", key=f"start_{assign['id']}"):
                    st.session_state.viewing_assignment_id = assign['id']
                    st.rerun()
    
    st.markdown("---")
    st.subheader("✅ Completed Assignments")
    if not completed_assignments:
        st.info("You have not completed any assignments yet.")
    else:
        for assign in completed_assignments:
            with st.container(border=True):
                st.markdown(f"**Topic:** {assign.get('topic', 'N/A')} (Completed)")
                st.caption(f"Due: {assign.get('due_date')}")
                # Future: Could add a button to review submission feedback here

    if st.button("Log Out"):
        del st.session_state.logged_in_student
        st.rerun()


# --- [NEW] Student Login Portal Function (Phase 2) ---
def render_student_login_portal():
    """Renders the main login page for students."""
    st.title("👨‍🎓 Student Portal Login")

    roster = load_db(CLASS_ROSTER_DB)
    if not roster:
        st.error("No classes are set up in the system yet. Please contact your teacher.")
        return

    # --- Login Form ---
    with st.form("student_login_form"):
        # 1. Select Class
        selected_student_id = None
        class_options = {cid: data["class_name"] for cid, data in roster.items()}
        selected_class_id = st.selectbox(
            "Select Your Class", 
            options=class_options.keys(), 
            format_func=lambda cid: class_options[cid],
            index=None,
            placeholder="Choose your class..."
        )

        if selected_class_id:
            # 2. Select Student (dynamically populates based on class)
            student_options = {s["student_id"]: s["name"] for s in roster[selected_class_id]["students"]}
            selected_student_id = st.selectbox(
                "Select Your Name",
                options=student_options.keys(),
                format_func=lambda sid: student_options[sid],
                index=None,
                placeholder="Find your name..."
            )
        
        # 3. Enter PIN
        student_pin = st.text_input("Enter your 4-Digit PIN", type="password", max_chars=4)

        login_button = st.form_submit_button("Login")

    if login_button:
        if not selected_class_id or not selected_student_id or not student_pin:
            st.error("Please fill out all fields.")
        else:
            # --- Authentication Logic ---
            student_data = None
            for s in roster[selected_class_id]["students"]:
                if s["student_id"] == selected_student_id:
                    student_data = s
                    break
            
            if student_data and student_data["pin"] == student_pin:
                st.success("Login Successful!")
                # Store logged in student in session state
                st.session_state.logged_in_student = {
                    "student_data": student_data,
                    "class_id": selected_class_id
                }
                st.rerun()
            else:
                st.error("Login failed. Check your name and PIN and try again.")

# def render_student_view(worksheet_id: str, ai_assistant: AITeacherAssistant):
#     """Displays a worksheet for a student, handles submission, and prevents re-submission."""
#     st.title("✍️ Complete Your Worksheet")
    
#     worksheets = load_db(WORKSHEETS_DB)
#     worksheet_data = worksheets.get(worksheet_id)

#     if not worksheet_data:
#         st.error("Worksheet not found. Please check the link or contact your teacher.")
#         return

#     st.header(f"Topic: {worksheet_data.get('topic', 'N/A')}")
#     st.caption(f"Class: {worksheet_data.get('standard')} | Board: {worksheet_data.get('board')} | Subject: {worksheet_data.get('subject')}")
#     st.markdown("---")
    
#     # Use session state to track submission status for this specific worksheet
#     submission_state_key = f"submitted_{worksheet_id}"
#     feedback_state_key = f"feedback_{worksheet_id}"

#     if submission_state_key not in st.session_state:
#         st.session_state[submission_state_key] = False
    
#     # --- State 1: Worksheet has been submitted ---
#     if st.session_state[submission_state_key]:
#         st.balloons() # The balloons are back!
#         st.success("✨ **Your worksheet has been submitted!**")
#         st.info("You have already completed this worksheet. Your feedback is shown below.")
        
#         # Display the stored feedback
#         if feedback_state_key in st.session_state:
#             _display_feedback_results(st.session_state[feedback_state_key])
#         return # Stop execution to prevent showing the form again

#     # --- State 2: Worksheet has NOT been submitted yet ---
#     worksheet_questions = worksheet_data.get("worksheet", [])

#     with st.form("submission_form"):
#         student_name = st.text_input("Please enter your name")
#         student_answers = {}
        
#         for i, q in enumerate(worksheet_questions):
#             q_key = f"q_{i}"
#             if q['type'] == 'mcq':
#                 student_answers[q_key] = st.radio(f"**{i+1}. {q['question']}**", options=q['options'], index=None, key=q_key)
#             elif q['type'] == 'fill_in_the_blank':
#                 student_answers[q_key] = st.text_input(f"**{i+1}. {q['question']}**", key=q_key)
#             elif q['type'] == 'short_answer':
#                 student_answers[q_key] = st.text_area(f"**{i+1}. {q['question']}**", key=q_key)
        
#         submitted = st.form_submit_button("Submit & Get Feedback")

#     if submitted:
#         if not student_name.strip():
#             st.warning("Please enter your name before submitting.")
#         else:
#             with st.spinner("AI is carefully grading your answers... Hang tight!"):
#                 # ... (The entire grading and saving logic remains exactly the same) ...
#                 all_feedback_for_overview = []
#                 incorrect_answers_report = []
#                 total_questions = len(worksheet_questions)
                
#                 for i, q in enumerate(worksheet_questions):
#                     grade_result = ai_assistant.get_semantic_grade_and_feedback(
#                         question=q['question'],
#                         student_answer=str(student_answers.get(f"q_{i}", "")),
#                         correct_answer=q['answer']
#                     )
                    
#                     is_correct = grade_result.get("grade", "Incorrect").lower() == "correct"
#                     feedback_text = grade_result.get("feedback", "Could not evaluate.")
#                     all_feedback_for_overview.append({"question": q['question'], "feedback": feedback_text})
                    
#                     if not is_correct:
#                         incorrect_answers_report.append({
#                             "question": q['question'],
#                             "your_answer": str(student_answers.get(f"q_{i}", "")),
#                             "correct_answer": q['answer'],
#                             "ai_feedback": feedback_text
#                         })

#                 ai_overview = ai_assistant.generate_performance_overview(
#                     student_name=student_name, topic=worksheet_data['topic'], all_feedback=all_feedback_for_overview
#                 )
                
#                 incorrect_count = len(incorrect_answers_report)
#                 score_percent = ((total_questions - incorrect_count) / total_questions) * 100 if total_questions > 0 else 0

#                 submissions = load_db(SUBMISSIONS_DB)
#                 submission_id = str(uuid.uuid4())
#                 submissions[submission_id] = {
#                     "worksheet_id": worksheet_id,
#                     "student_name": student_name.strip(),
#                     "topic": worksheet_data.get('topic'),
#                     "answers": student_answers,
#                     "feedback": incorrect_answers_report,
#                     "score_percent": score_percent,
#                     "ai_overview": ai_overview,
#                     "submitted_at": pd.Timestamp.now().isoformat()
#                 }
#                 save_db(submissions, SUBMISSIONS_DB)

#                 # Store feedback in session state and set submission flag
#                 st.session_state[feedback_state_key] = {
#                     "ai_overview": ai_overview,
#                     "feedback_report": incorrect_answers_report
#                 }
#                 st.session_state[submission_state_key] = True
                
#                 # Rerun the script to show the "submitted" view
#                 st.rerun()

def render_teacher_dashboard(ai_assistant):
    """Displays the main dashboard for the teacher."""
    st.title("👨‍🏫 Teacher's AI Assistant Dashboard")

    # --- NEW: Initialize session state for the editing workflow ---
    if 'draft_worksheet' not in st.session_state:
        st.session_state.draft_worksheet = None
    if 'finalized_link' not in st.session_state:
        st.session_state.finalized_link = None
    if 'confirm_delete_selection' not in st.session_state:
        st.session_state.confirm_delete_selection = False
    if 'worksheet_to_assign' not in st.session_state:
        st.session_state.worksheet_to_assign = None
        

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Worksheet Generator", "View Submissions", "Student Progress Tracker", "Class Insights", "Class Management"])

# --- Worksheet Generator Tab ---
    
    with tab1:
        st.header("Worksheet Generator")
        
        # Add radio button to select worksheet type
        worksheet_type = st.radio("Select Worksheet Type", ["General Worksheet", "Adaptive Worksheet"], horizontal=True)
        
        if worksheet_type == "General Worksheet":
            st.subheader("Generate General Worksheet")
            
            # Hide the generation form if a draft is already being edited
            if st.session_state.draft_worksheet is None:
                
                # Load all unique, normalized topics that have already been assigned
                # This helps the teacher maintain consistency.
                assignments_db = load_db(ASSIGNMENTS_DB)
                existing_topics = sorted(list(set(a['topic'] for a in assignments_db.values())))
            
                with st.form("worksheet_form"):
                    standard = st.selectbox("Standard (Class)", ["9", "10", "11", "12"], key="general_standard")
                    board = st.selectbox("Board", ["CBSE", "ICSE", "State Board"], key="general_board")
                    subject = st.text_input("Subject", "Science", key="general_subject")
                    st.markdown("---")
                    topic = st.text_input("Topic", "Cell Structure", key="general_topic")
                    if existing_topics:
                        with st.expander("Show existing topics (for consistency)"):
                            st.caption("Tip: To keep analytics clean, try to re-use an existing topic name if it already exists.")
                            st.dataframe(pd.Series(existing_topics, name="Existing Topics"), use_container_width=True, hide_index=True)
                    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], key="general_difficulty")
                    num_questions = st.number_input("Number of Questions", min_value=3, max_value=15, value=5, key="general_num_questions")
                    submitted = st.form_submit_button("Generate Worksheet Draft")
                
                if submitted:
                    with st.spinner("Validating topic against subject..."):
                        is_valid_topic = ai_assistant.validate_topic_for_subject(standard, board, subject, topic)
                    
                    if not is_valid_topic:
                        st.error(f"**Topic Mismatch:** The topic '{topic}' seems invalid for {subject} in Class {standard}. Please check and try again.", icon="🚨")
                    else:
                        with st.spinner("AI is creating the worksheet..."):
                            worksheet_content = ai_assistant.generate_mixed_worksheet(standard, board, subject, topic, difficulty, num_questions)
                            if worksheet_content and "worksheet" in worksheet_content:
                                st.session_state.draft_worksheet = {
                                    "standard": standard, "board": board, "subject": subject,
                                    "topic": topic, "difficulty": difficulty, **worksheet_content
                                }
                                st.session_state.finalized_link = None
                                st.rerun()
                            else:
                                st.error("Failed to generate worksheet content. The AI might be busy, please try again.")
        
        else:  # Adaptive Worksheet
            st.subheader("Generate Adaptive Worksheet")
            submissions = load_db(SUBMISSIONS_DB)
            all_students = sorted(list(set(data['student_name'] for data in submissions.values() if 'student_name' in data)))
            
            if not all_students:
                st.info("No students with submissions found.")
            else:
                selected_student = st.selectbox("Select Student", options=all_students, key="adaptive_student")
                
                if selected_student:
                    student_submissions = {sub_id: data for sub_id, data in submissions.items() if data.get('student_name') == selected_student}
                    
                    if not student_submissions:
                        st.info(f"No submissions found for {selected_student}.")
                    else:
                        student_topics = sorted(list(set(data.get('topic', 'Unknown') for data in student_submissions.values())))
                        if not student_topics:
                            st.info(f"No topics found for {selected_student}'s submissions. Use the general worksheet generator instead.")
                        else:
                            all_feedback = []
                            for data in student_submissions.values():
                                topic = data.get('topic', 'Unknown')
                                for item in data.get('feedback', []):
                                    all_feedback.append({
                                        "topic": topic,
                                        "question": item['question'],
                                        "your_answer": item['your_answer'],
                                        "correct_answer": item['correct_answer'],
                                        "feedback": item['ai_feedback']
                                    })
                            
                            if not all_feedback:
                                st.info(f"{selected_student} has no incorrect answers in previous submissions. Use the general worksheet generator instead.")
                            else:
                                performance_summary = "\n".join([
                                    f"Topic: {item['topic']}\nQuestion: {item['question']}\nStudent Answer: {item['your_answer']}\nCorrect Answer: {item['correct_answer']}\nAI Feedback: {item['feedback']}\n---"
                                    for item in all_feedback
                                ])
                                
                                with st.form("adaptive_worksheet_form"):
                                    standard = st.selectbox("Standard (Class)", ["9", "10", "11", "12"], key="adaptive_standard")
                                    board = st.selectbox("Board", ["CBSE", "ICSE", "State Board"], key="adaptive_board")
                                    subject = st.text_input("Subject", "Science", key="adaptive_subject")
                                    
                                    # Topic dropdown with previously attempted topics only
                                    topic = st.selectbox("Topic", options=student_topics, key="adaptive_topic")
                                    
                                    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], key="adaptive_difficulty")
                                    num_questions = st.number_input("Number of Questions", min_value=3, max_value=15, value=5, key="adaptive_num_questions")
                                    submitted = st.form_submit_button("Generate Adaptive Worksheet Draft")
                                
                                if submitted:
                                    if not topic.strip() or not subject.strip():
                                        st.warning("Please enter or select a valid subject and topic.")
                                    else:
                                        with st.spinner("Validating topic against subject..."):
                                            is_valid_topic = ai_assistant.validate_topic_for_subject(standard, board, subject, topic)
                                        
                                        if not is_valid_topic:
                                            st.error(f"**Topic Mismatch:** The topic '{topic}' seems invalid for {subject} in Class {standard}. Please check and try again.", icon="🚨")
                                        else:
                                            with st.spinner("AI is creating the adaptive worksheet..."):
                                                worksheet_content = ai_assistant.generate_adaptive_worksheet(standard, board, subject, topic, difficulty, num_questions, performance_summary)
                                                if worksheet_content and "worksheet" in worksheet_content:
                                                    st.session_state.draft_worksheet = {
                                                        "standard": standard, "board": board, "subject": subject,
                                                        "topic": topic, "difficulty": difficulty, **worksheet_content
                                                    }
                                                    st.session_state.finalized_link = None
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to generate worksheet content. The AI might be busy, please try again.")
        
        # --- Worksheet Editor UI ---
        if st.session_state.draft_worksheet:
            st.header("Review and Edit Worksheet")
            st.info("Modify the questions/answers. When done, click 'Save and Finalize' to proceed to the assignment step.")
            
            with st.form("edit_worksheet_form"):
                draft = st.session_state.draft_worksheet
                st.text_input("Worksheet Topic", value=draft.get('topic', ''), key="edit_topic")
                
                for i, q in enumerate(draft["worksheet"]):
                    with st.container(border=True):
                        st.markdown(f"**Editing Question {i+1} ({q.get('type', 'N/A')})**")
                        st.text_area("Question Text:", value=q['question'], key=f"q_{i}_text", height=100)
                        
                        if q['type'] == 'mcq':
                            st.markdown("Options (the first one should be the correct answer):")
                            cols = st.columns(2)
                            correct_answer_text = q['answer']
                            options_list = list(q['options'])
                            if correct_answer_text in options_list:
                                options_list.remove(correct_answer_text)
                            sorted_options = [correct_answer_text] + options_list
                            
                            for opt_idx in range(4):
                                cols[opt_idx % 2].text_input(
                                    f"Option {opt_idx + 1}", 
                                    value=sorted_options[opt_idx] if opt_idx < len(sorted_options) else "",
                                    key=f"q_{i}_opt_{opt_idx}"
                                )
                        else:
                            st.text_input("Correct Answer:", value=q['answer'], key=f"q_{i}_ans")
                
                finalize_button = st.form_submit_button("✅ Save and Finalize Worksheet", type="primary")
                
            if finalize_button:
                with st.spinner("Saving your changes..."):
                    updated_worksheet_data = st.session_state.draft_worksheet.copy()
                    
                    # --- THIS IS THE FIX ---
                    # Normalize the topic to prevent fragmentation in analytics
                    final_topic = st.session_state.edit_topic.strip().lower()
                    # --- END FIX ---

                    updated_worksheet_data['topic'] = final_topic
            
                    final_questions = []
                    for i, q in enumerate(updated_worksheet_data["worksheet"]):
                        new_q = q.copy()
                        new_q['question'] = st.session_state[f"q_{i}_text"]
                        
                        if new_q['type'] == 'mcq':
                            new_options = [st.session_state[f"q_{i}_opt_{j}"] for j in range(4)]
                            new_q['options'] = new_options
                            new_q['answer'] = new_options[0]
                        else:
                            new_q['answer'] = st.session_state[f"q_{i}_ans"]
                        final_questions.append(new_q)
                    
                    updated_worksheet_data["worksheet"] = final_questions
                    worksheet_id = str(uuid.uuid4())
                    worksheets = load_db(WORKSHEETS_DB)
                    worksheets[worksheet_id] = updated_worksheet_data
                    save_db(worksheets, WORKSHEETS_DB)
                    
                    # --- THIS IS THE KEY CHANGE ---
                    st.session_state.worksheet_to_assign = {"id": worksheet_id, "topic": final_topic}
                    st.session_state.draft_worksheet = None # Clear the draft
                    st.session_state.finalized_link = None # Clear the old state
                    st.rerun()

        # --- UI State 3: Assign Finalized Worksheet ---
        elif st.session_state.worksheet_to_assign:
            st.header(f"Assign Worksheet: '{st.session_state.worksheet_to_assign['topic']}'")
            st.success("Worksheet saved! Now, assign it to a class.")

            roster_data = load_db(CLASS_ROSTER_DB)
            if not roster_data:
                st.error("You have not created any classes. Please go to the 'Class Management' tab to create a class first.")
                if st.button("Cancel Assignment"):
                    st.session_state.worksheet_to_assign = None
                    st.rerun()
            else:
                with st.form("assign_form"):
                    class_options = {cid: data["class_name"] for cid, data in roster_data.items()}
                    selected_class_id = st.selectbox(
                        "Select Class to Assign",
                        options=class_options.keys(),
                        format_func=lambda cid: class_options[cid]
                    )
                    # --- THIS IS THE FEATURE YOU WERE MISSING ---
                    due_date = st.date_input("Select Due Date", min_value=datetime.date.today())
                    
                    submit_assignment = st.form_submit_button("Assign to Class", type="primary")

                if submit_assignment:
                    with st.spinner("Assigning worksheet..."):
                        assignments_db = load_db(ASSIGNMENTS_DB)
                        assignment_id = str(uuid.uuid4())
                        
                        assignments_db[assignment_id] = {
                            "worksheet_id": st.session_state.worksheet_to_assign['id'],
                            "class_id": selected_class_id,
                            "topic": st.session_state.worksheet_to_assign['topic'], # Denormalize topic
                            "assigned_date": pd.Timestamp.now().strftime('%Y-%m-%d'),
                            "due_date": due_date.strftime('%Y-%m-%d')
                        }
                        
                        save_db(assignments_db, ASSIGNMENTS_DB)
                        st.session_state.worksheet_to_assign = None # Clear the state
                        st.success(f"Worksheet successfully assigned to {class_options[selected_class_id]}!")
                        st.balloons()
                
                if st.button("Cancel Assignment Process"):
                    st.session_state.worksheet_to_assign = None
                    st.rerun()

            if st.session_state.worksheet_to_assign is None and st.button("Create Another Worksheet"):
                st.rerun()
                    
    # --- View Submissions Tab ---
    # ==============================================================================
    # --- TAB 2: MARKBOOK 
    with tab2:
        st.header("📖 Markbook & Assignment Status")

        # Load all necessary databases
        assignments_db = load_db(ASSIGNMENTS_DB)
        roster_db = load_db(CLASS_ROSTER_DB)
        submissions_db = load_db(SUBMISSIONS_DB)

        if not assignments_db:
            st.info("No assignments have been created yet. Go to the 'Worksheet Generator' to assign one.")
        else:
            # --- 1. Select an Assignment ---
            # Sort assignments to show newest first
            sorted_assignments = sorted(
                assignments_db.items(), 
                key=lambda item: item[1]['assigned_date'], 
                reverse=True
            )
            
            assignment_options = {aid: f"{data['topic']} (Due: {data['due_date']})" for aid, data in sorted_assignments}
            
            selected_aid = st.selectbox(
                "Select an Assignment to review:",
                options=assignment_options.keys(),
                format_func=lambda aid: assignment_options[aid],
                index=None,
                placeholder="Choose an assignment..."
            )

            if selected_aid:
                # --- 2. Build the Markbook for the selected assignment ---
                assignment_data = assignments_db[selected_aid]
                class_id = assignment_data['class_id']
                
                if class_id not in roster_db:
                    st.error(f"Error: The class associated with this assignment (ID: {class_id}) no longer exists in the roster.")
                    st.stop()

                student_roster = roster_db[class_id].get('students', [])
                if not student_roster:
                    st.warning("This class has no students in the roster.")
                    st.stop()

                # Find all submissions for THIS assignment
                assignment_submissions = {} # Use a dict for fast lookup by student_id
                for sub_id, sub_data in submissions_db.items():
                    if sub_data.get('assignment_id') == selected_aid:
                        assignment_submissions[sub_data['student_id']] = sub_data
                
                # --- 3. Generate Status List & KPIs ---
                markbook_list = []
                total_students = len(student_roster)
                num_submitted = 0
                total_score = 0
                
                due_date = pd.to_datetime(assignment_data['due_date'])
                is_past_due = pd.Timestamp.now() > due_date

                for student in student_roster:
                    student_id = student['student_id']
                    submission = assignment_submissions.get(student_id)
                    
                    if submission:
                        num_submitted += 1
                        score = submission.get('score_percent', 0)
                        total_score += score
                        markbook_list.append({
                            "Student Name": student['name'],
                            "Status": "✅ Submitted",
                            "Submitted At": pd.to_datetime(submission['submitted_at']).strftime('%Y-%m-%d %H:%M'),
                            "Score (%)": score,
                            "Submission ID": submission['assignment_id'] # Using assignment_id for consistency, could be real sub_id
                        })
                    else:
                        status = "❌ Missing (Past Due)" if is_past_due else "Not Started"
                        markbook_list.append({
                            "Student Name": student['name'],
                            "Status": status,
                            "Submitted At": "N/A",
                            "Score (%)": None,
                            "Submission ID": None
                        })

                # --- 4. Display KPIs & Markbook Table ---
                completion_rate = (num_submitted / total_students) * 100 if total_students > 0 else 0
                avg_score = (total_score / num_submitted) if num_submitted > 0 else 0

                st.markdown("---")
                st.subheader(f"Status for: {assignment_data['topic']}")
                
                kpi_cols = st.columns(3)
                kpi_cols[0].metric("Total Students", f"{total_students}")
                kpi_cols[1].metric("Completion Rate", f"{completion_rate:.1f}%")
                kpi_cols[2].metric("Class Average (on submitted)", f"{avg_score:.1f}%")

                markbook_df = pd.DataFrame(markbook_list)
                st.dataframe(markbook_df, use_container_width=True, hide_index=True)

                st.markdown("---")
                
                # --- 5. Submission Detail Viewer (Preserved functionality) ---
                st.subheader("View Individual Submission Details")
                
                # Filter dropdown to only students who HAVE submitted
                submitted_students_map = {
                    sub_data['student_id']: sub_data['student_name']
                    for sub_data in assignment_submissions.values()
                }

                if not submitted_students_map:
                    st.info("No submissions yet for this assignment.")
                else:
                    selected_student_id = st.selectbox(
                        "Select a submitted student to view details:",
                        options=submitted_students_map.keys(),
                        format_func=lambda sid: submitted_students_map[sid]
                    )

                    if selected_student_id:
                        selected_sub_data = assignment_submissions[selected_student_id]
                        st.write(f"#### Details for {selected_sub_data['student_name']}")
                        
                        st.info("**AI Performance Overview:**")
                        overview = selected_sub_data.get('ai_overview')
                        if overview:
                            st.markdown(overview)
                        else:
                            st.warning("No AI overview was generated for this submission.")
                        
                        with st.expander("See detailed raw submission data"):
                            st.json(selected_sub_data)
    
    with tab3:
        st.header("🎓 Student Progress Tracker")
        submissions = load_db(SUBMISSIONS_DB)
        if not submissions:
            st.info("No submission data available to track progress.")
        else:
            all_students = sorted(list(set(data['student_name'] for data in submissions.values())))
            
            if not all_students:
                st.info("No submissions with student names found.")
                return
            
            selected_student = st.selectbox("Select a Student to Track Progress", options=all_students)

            if selected_student:
                student_data = []
                for sub_id, data in submissions.items():
                    if data['student_name'] == selected_student:
                        student_data.append({
                            "Date": pd.to_datetime(data['submitted_at']),
                            "Topic": data.get('topic', 'N/A'),
                            "Score (%)": data.get('score_percent', 0)
                        })
                
                if not student_data:
                    st.warning(f"No submissions found for {selected_student}.")
                else:
                    progress_df = pd.DataFrame(student_data).sort_values(by="Date")
                    st.subheader(f"Performance History for {selected_student}")
                    
                    # --- MODIFIED: Use bar_chart instead of line_chart ---
                    # 1. Create the figure
                    fig = px.bar(
                        progress_df, 
                        x="Date", 
                        y="Score (%)",
                        title=f"Worksheet Scores for {selected_student}",
                        text="Score (%)" # Use the score column for the text labels
                    )
                    
                    # 2. Customize the appearance
                    fig.update_traces(
                        texttemplate='%{text:.0f}%', # Format the text as a percentage
                        textposition='outside' # Place the text label above the bar
                    )
                    
                    fig.update_layout(
                        uniformtext_minsize=8, 
                        uniformtext_mode='hide',
                        bargap=0.3, # Adjust gap to make bars appear wider
                        yaxis_title="Score (Percentage)",
                        xaxis_title="Submission Date"
                    )

                    # 3. Set the Y-axis range to 0-100
                    fig.update_yaxes(range=[0, 100])

                    # 4. Display the chart in Streamlit
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(progress_df, use_container_width=True)
                    
    # Add this entire block at the end of the render_teacher_dashboard function

    with tab4:
        st.header("🔬 Class Insights")
        submissions = load_db(SUBMISSIONS_DB)

        if not submissions:
            st.info("No submission data available to generate insights.")
        else:
            # --- 1. Weak Area Heatmap ---
            st.subheader("Weak Area Analysis by Topic")
            
            topic_errors = defaultdict(int)
            topic_student_errors = defaultdict(set)

            for sub_id, data in submissions.items():
                if data.get("feedback"): # If there were incorrect answers
                    topic = data.get("topic", "Uncategorized")
                    student_name = data.get("student_name", "Unknown")
                    topic_errors[topic] += len(data["feedback"])
                    topic_student_errors[topic].add(student_name)

            if not topic_errors:
                st.success("🎉 No common weak areas found! Students are performing well across all topics.")
            else:
                error_df = pd.DataFrame(list(topic_errors.items()), columns=['Topic', 'Number of Errors']).sort_values(by='Number of Errors', ascending=False)
                
                fig = px.treemap(error_df, path=['Topic'], values='Number of Errors',
                                title='Heatmap of Weak Areas (Topics with Most Errors)',
                                color='Number of Errors', color_continuous_scale='Reds')
                fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
                st.plotly_chart(fig, use_container_width=True)

                weakest_topic = error_df.iloc[0]
                st.warning(f"The most challenging topic appears to be **'{weakest_topic['Topic']}'** with **{weakest_topic['Number of Errors']}** recorded errors.")

                if st.button(f"Generate Remediation Plan for '{weakest_topic['Topic']}'"):
                    with st.spinner(f"Generating a plan for {weakest_topic['Topic']}..."):
                        student_count = len(topic_student_errors[weakest_topic['Topic']])
                        plan = ai_assistant.generate_class_remediation_plan(
                            topic=weakest_topic['Topic'],
                            error_count=int(weakest_topic['Number of Errors']),
                            student_count=student_count
                        )
                        st.info(f"**Suggested Plan for '{weakest_topic['Topic']}'**")
                        st.markdown(plan)

            st.markdown("---")

            # --- 2. At-Risk Student Identifier ---
            st.subheader("At-Risk Student Identifier")
            
            student_performance = defaultdict(list)
            for sub_id, data in submissions.items():
                name = data.get("student_name")
                if not name:
                    continue
                student_performance[name].append({
                    "score": data.get("score_percent", 0),
                    "date": pd.to_datetime(data.get("submitted_at")),
                    "topic": data.get("topic", "N/A")
                })

            at_risk_students = []
            for name, subs in student_performance.items():
                if not subs:
                    continue
                
                df = pd.DataFrame(subs).sort_values(by="date", ascending=False)
                avg_score = df['score'].mean()
                last_score = df['score'].iloc[0]
                submission_count = len(df)
                
                # Define at-risk criteria: avg score < 70 AND last score is also below 70
                if avg_score < 70 and last_score < 70:
                    struggling_topics = ", ".join(list(set(sub['topic'] for sub in subs if sub['score'] < 100)))
                    at_risk_students.append({
                        "Student Name": name,
                        "Average Score (%)": f"{avg_score:.1f}",
                        "Most Recent Score (%)": f"{last_score:.1f}",
                        "Submissions": submission_count,
                        "performance_summary": (
                            f"- Overall Average Score: {avg_score:.1f}%\n"
                            f"- Most Recent Score: {last_score:.1f}%\n"
                            f"- Number of worksheets submitted: {submission_count}\n"
                            f"- Topics with errors: {struggling_topics}"
                        )
                    })

            if not at_risk_students:
                st.success("✅ No students are currently flagged as at-risk. Great work by everyone!")
            else:
                st.warning(f"Found {len(at_risk_students)} student(s) who might need extra support based on recent performance.")
                
                display_df = pd.DataFrame(at_risk_students)[["Student Name", "Average Score (%)", "Most Recent Score (%)", "Submissions"]]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                at_risk_names = [s["Student Name"] for s in at_risk_students]
                selected_student_name = st.selectbox("Select a student to generate a personalized remediation plan:", options=at_risk_names)
                
                if selected_student_name:
                    if st.button(f"Generate Plan for {selected_student_name}"):
                        student_to_help = next((s for s in at_risk_students if s["Student Name"] == selected_student_name), None)
                        if student_to_help:
                            with st.spinner(f"Creating a personalized plan for {selected_student_name}..."):
                                plan = ai_assistant.generate_student_remediation_plan(
                                    student_name=selected_student_name,
                                    performance_summary=student_to_help["performance_summary"]
                                )
                                st.info(f"**Personalized Plan for {selected_student_name}**")
                                st.markdown(plan)
    with tab5:
        st.header("🎓 Class Roster Management")
        st.info("Create your classes here, then add students to each class. This is the first step to assigning worksheets.")

        roster_data = load_db(CLASS_ROSTER_DB)

        col1, col2 = st.columns(2)

        # --- Column 1: Create Class & Add Students ---
        with col1:
            # --- Form to Create a New Class ---
            with st.form("new_class_form", clear_on_submit=True):
                st.subheader("1. Create a New Class")
                new_class_name = st.text_input("New Class Name (e.g., 'Class 10A - Physics')")
                submitted_class = st.form_submit_button("Create Class")
                
                if submitted_class:
                    if not new_class_name.strip():
                        st.warning("Please enter a class name.")
                    else:
                        class_id = str(uuid.uuid4())
                        roster_data[class_id] = {
                            "class_name": new_class_name.strip(),
                            "students": []
                        }
                        save_db(roster_data, CLASS_ROSTER_DB)
                        st.success(f"Class '{new_class_name}' created!")
                        st.rerun()

            st.markdown("---")

            # --- Form to Add Students to a Class ---
            if not roster_data:
                st.info("Create a class before you can add students.")
            else:
                with st.form("new_student_form", clear_on_submit=True):
                    st.subheader("2. Add Students to Class")
                    
                    # Create dropdown options from the loaded roster data
                    class_options = {cid: data["class_name"] for cid, data in roster_data.items()}
                    selected_class_id = st.selectbox(
                        "Select Class", 
                        options=class_options.keys(), 
                        format_func=lambda cid: class_options[cid]
                    )
                    
                    new_student_name = st.text_input("New Student's Full Name")
                    new_student_pin = st.text_input("Create 4-Digit PIN", max_chars=4, type="password")
                    
                    submitted_student = st.form_submit_button("Add Student")

                    if submitted_student:
                        if not new_student_name.strip() or not new_student_pin.strip():
                            st.warning("Please provide both a student name and a PIN.")
                        elif not (new_student_pin.isdigit() and len(new_student_pin) == 4):
                            st.warning("PIN must be exactly 4 digits.")
                        else:
                            student_id = str(uuid.uuid4())
                            new_student_data = {
                                "student_id": student_id,
                                "name": new_student_name.strip(),
                                "pin": new_student_pin
                            }
                            # Append the student to the correct class list
                            roster_data[selected_class_id]["students"].append(new_student_data)
                            save_db(roster_data, CLASS_ROSTER_DB)
                            st.success(f"Student '{new_student_name}' added to {class_options[selected_class_id]}!")
                            st.rerun()

        # --- Column 2: View Current Rosters ---
        # --- Column 2: View and Manage Current Rosters ---
        with col2:
            st.subheader("Current Class Rosters")
            if not roster_data:
                st.info("No classes created yet.")
            else:
                for class_id, data in roster_data.items():
                    with st.expander(f"**{data['class_name']}** ({len(data['students'])} students)"):
                        st.write(f"*Class ID: `{class_id}`*")
                        
                        if not data['students']:
                            st.info("No students have been added to this class yet.")
                        else:
                            # Display the roster in a clean table
                            student_df = pd.DataFrame(data['students'])
                            st.dataframe(student_df, use_container_width=True, hide_index=True)

                            st.markdown("---")
                            
                            # --- FEATURE 1: Delete a specific student ---
                            with st.form(key=f"delete_student_{class_id}"):
                                st.markdown("**Delete a Student:**")
                                student_options = {s['student_id']: s['name'] for s in data['students']}
                                student_to_delete = st.selectbox(
                                    "Select student to remove:", 
                                    options=student_options.keys(), 
                                    format_func=lambda sid: student_options[sid]
                                )
                                if st.form_submit_button("Remove Student from Class", type="primary"):
                                    # Rebuild the student list excluding the selected student
                                    roster_data[class_id]['students'] = [
                                        s for s in roster_data[class_id]['students'] if s['student_id'] != student_to_delete
                                    ]
                                    save_db(roster_data, CLASS_ROSTER_DB)
                                    st.success(f"Removed {student_options[student_to_delete]} from the class.")
                                    st.rerun()

                        st.markdown("---")
                        
                        # --- FEATURE 2: Delete the entire class (with confirmation) ---
                        st.markdown("**Delete This Class:**")
                        
                        # Initialize confirmation state
                        confirm_key = f"confirm_delete_class_{class_id}"
                        if confirm_key not in st.session_state:
                            st.session_state[confirm_key] = False
                            
                        if st.button("Delete This Entire Class", type="primary", key=f"delete_class_trigger_{class_id}"):
                            st.session_state[confirm_key] = True # Trigger confirmation

                        # Show confirmation dialogue if triggered
                        if st.session_state.get(confirm_key, False):
                            st.warning(f"**Are you sure you want to permanently delete the class '{data['class_name']}'?** All students in it will be removed. This cannot be undone.")
                            c1, c2 = st.columns(2)
                            if c1.button("✅ Yes, permanently delete", key=f"confirm_yes_{class_id}"):
                                del roster_data[class_id] # Delete the class from the dict
                                save_db(roster_data, CLASS_ROSTER_DB)
                                del st.session_state[confirm_key] # Clean up state
                                st.success("Class successfully deleted.")
                                st.rerun()
                            if c2.button("Cancel", key=f"confirm_no_{class_id}"):
                                st.session_state[confirm_key] = False # Reset state
                                st.rerun()

    
# ==============================================================================
# --- Main App Router  ---
# ==============================================================================
st.set_page_config(page_title="Interactive Teacher AI", layout="wide")

ai_assistant = get_ai_assistant()
query_params = st.query_params

# Check if teacher is logging in
if "view" in query_params and query_params["view"] == "teacher":
    render_teacher_dashboard(ai_assistant)

# Check if a student is already logged in
elif "logged_in_student" in st.session_state:
    student_info = st.session_state.logged_in_student
    render_student_dashboard(student_info["student_data"], student_info["class_id"], ai_assistant)

# Default to the student login portal
else:
    render_student_login_portal()