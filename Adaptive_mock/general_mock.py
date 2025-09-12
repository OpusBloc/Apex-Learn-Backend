import os
import streamlit as st
from dotenv import load_dotenv
import logging
import time
import json
import random
import pandas as pd
import altair as alt
from typing import Optional, List
from openai import OpenAI
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

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)


# --- Data Loading ---
def load_student_data():
    """Loads student data from the JSON file."""
    try:
        with open('student_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("`student_data.json` not found. Please ensure the file is in the same directory.")
        return []
    except json.JSONDecodeError:
        st.error("Error decoding `student_data.json`. Please ensure it's a valid JSON file.")
        return []

def save_student_data(updated_profile):
    """Finds the user, updates their data, and saves the entire list back to the file."""
    all_data = st.session_state.student_data
    user_id_to_update = updated_profile.get("user_id")

    index_to_update = -1
    for i, user in enumerate(all_data):
        if user.get("user_id") == user_id_to_update:
            index_to_update = i
            break
    
    if index_to_update != -1:
        all_data[index_to_update] = updated_profile
        try:
            with open('student_data.json', 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=4)
            
            # Update the master data in session state to stay in sync
            st.session_state.student_data = all_data 
            st.success("Progress saved successfully!") # VISIBLE SUCCESS
        except Exception as e:
            # SHOW a visible error message in the app
            st.error(f"CRITICAL: Failed to save data. Reason: {e}")
    else:
        st.warning(f"Could not find user {user_id_to_update} to save data.")

def start_test(subject, q_count, weak_topics, focus_topic):
    """Helper function to generate and start a test."""
    
    st.session_state.test_results = []
    st.session_state.focus_topic = focus_topic
    
    with st.spinner("Analyzing your profile and crafting questions..."):
        profile = st.session_state.user_profile
        
        st.session_state.current_subject = subject

        quiz_questions = generate_interactive_test_with_llm(
            board=profile['board'],
            subject=subject,
            student_class=profile['class'],
            question_count=q_count,
            focus_topic=focus_topic,
            weak_topics=weak_topics
        )

        if quiz_questions:
            st.session_state.current_test = quiz_questions
            st.session_state.current_question_index = 0
            st.session_state.quiz_mode = "active"
            st.rerun()
        else:
            st.error("Sorry, I had trouble generating a test. There might be an issue with the prompt or network. Please try again.")


# --- Core LLM Function for Quiz Generation ---

def generate_interactive_test_with_llm(
    board: str,
    subject: str,
    student_class: str,
    question_count: int,
    focus_topic: Optional[str] = None,
    weak_topics: Optional[List[str]] = None
) -> list:
    """
    Generates a structured, syllabus-aware MCQ test in JSON format using the OpenAI API.
    """
    logger.info(
        f"Generating test for: Board='{board}', Class='{student_class}', Subject='{subject}', "
        f"Topic='{focus_topic}', Weak Topics='{weak_topics}'"
    )

    prompt = (
        f"You are an expert curriculum designer for Indian school boards. "
        f"Your task is to create a quiz for a Class {student_class} student studying {subject} under the {board} board.\n"
        f"Generate exactly {question_count} multiple-choice questions in a strict JSON format.\n"
    )

    if focus_topic:
        prompt += (
            f"The quiz MUST focus exclusively on the topic: '{focus_topic}'. "
            f"Ensure all questions are relevant to this specific topic as it appears in the {board} Class {student_class} {subject} syllabus.\n"
        )
    elif weak_topics:
        prompt += (
            f"This is a personalized test. Prioritize generating questions from the student's weaker topics: {', '.join(weak_topics)}. "
            f"You can also include 1-2 questions from other related areas to ensure variety.\n"
        )
    else:
        prompt += f"The quiz should cover a general range of important topics from the {board} Class {student_class} {subject} syllabus.\n"

    prompt += (
        "\nFor each question, you must:\n"
        "1. Identify a specific, granular topic from the syllabus (e.g., 'Trigonometric Ratios', not just 'Trigonometry').\n"
        "2. Assign a difficulty level: 'Easy', 'Medium', or 'Hard'.\n"
        "3. Provide the correct answer and three plausible but incorrect 'distractors'.\n"
        "4. Provide a clear, step-by-step 'explanation' for how to arrive at the correct answer. For math, show the steps.\n"  # <-- NEW INSTRUCTION
        "5. Ensure the question and options adhere to the specified curriculum and class level.\n\n"
        "**CRITICAL REQUIREMENT: All questions generated MUST be of the 'MCQ' type.**\n"
        "**Output MUST be a valid JSON array (`[]`) of objects (`{}`). Do not include any text, notes, or apologies outside the JSON structure.**\n"
        "Example format for a single MCQ object:\n"
        "{\n"
        "  \"question_text\": \"If a rectangle has a length of 8 cm and a width of 5 cm, what is its area?\",\n"
        "  \"question_type\": \"MCQ\",\n"
        "  \"topic\": \"Area and Perimeter\",\n"
        "  \"difficulty\": \"Easy\",\n"
        "  \"answer\": \"40 sq cm\",\n"
        "  \"distractors\": [\"13 cm\", \"26 sq cm\", \"32 sq cm\"],\n"
        "  \"explanation\": \"The formula for the area of a rectangle is Length × Width. In this case, Area = 8 cm × 5 cm = 40 sq cm.\"\n"  # <-- NEW FIELD IN EXAMPLE
        "}\n"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # Using a powerful model for accuracy
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        response_content = response.choices[0].message.content
        # The response should be a JSON object containing a list, let's find the list.
        json_data = json.loads(response_content)
        # Assuming the model might wrap the list in a key like "questions"
        for key, value in json_data.items():
            if isinstance(value, list):
                return value
        return [] # Return empty if no list is found
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Error parsing LLM response: {e}\nResponse: {response_content}")
        return []


def get_weakest_topics(profile: dict, subject: str, count: int = 3) -> list:
    """Identifies the topics with the lowest accuracy for a given subject."""
    subject_performance = profile.get(subject)
    if not subject_performance:
        return []

    topic_accuracies = []
    for topic, data in subject_performance.items():
        if data['total'] > 0:
            accuracy = data['correct'] / data['total']
            topic_accuracies.append({'topic': topic, 'accuracy': accuracy})

    # Sort topics by accuracy (lowest first)
    sorted_topics = sorted(topic_accuracies, key=lambda x: x['accuracy'])
    return [item['topic'] for item in sorted_topics[:count]]


# --- Streamlit UI ---

# --- Session State Initialization ---
# --- Session State Initialization ---
if 'student_data' not in st.session_state:
    st.session_state.student_data = load_student_data()
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'performance_profile' not in st.session_state:
    st.session_state.performance_profile = None # Will be loaded on login
if 'current_test' not in st.session_state:
    st.session_state.current_test = None
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'quiz_mode' not in st.session_state:
    st.session_state.quiz_mode = "setup"

st.title("🎯 Personalized Mock Test Generator")

# --- Login Gate ---
if not st.session_state.user_id:
    st.subheader("Welcome! Please select your profile to begin.")
    user_ids = [user['user_id'] for user in st.session_state.student_data]
    if not user_ids:
        st.warning("No student data found. Please check your `student_data.json` file.")
    else:
        selected_user_id = st.selectbox("Select User ID", options=user_ids)

        if st.button("Login"):
            st.session_state.user_id = selected_user_id
            st.session_state.user_profile = next((item for item in st.session_state.student_data if item["user_id"] == selected_user_id), None)
            st.session_state.performance_profile = st.session_state.user_profile.get('performance_data_per_subject', {})
            st.rerun()
else:
    # --- Main App UI (after login) ---
    st.sidebar.success(f"Logged in as: **{st.session_state.user_id}**")
    if st.sidebar.button("Logout"):
        # Clear the session to log out
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- UI TABS ---
    tab1, tab2 = st.tabs(["📝 Generate Test", "📊 Analytics Dashboard"])
    
    with tab1:
        # --- Test Setup & Suggestion Dashboard ---
        if st.session_state.quiz_mode == "setup":
            st.subheader(f"Hello! Here are your suggested mock tests.")
            
            performance_data = st.session_state.performance_profile

            # --- Compulsory Mock Tests ---
            st.markdown("---")
            st.header("Subject Tests")
            st.write("These adaptive tests focus on your weak points in subjects you've covered extensively.")

            # A "covered" subject has data for at least 2 topics.
            covered_subjects = [
                subject for subject, topics in performance_data.items() if len(topics) >= 2
            ]

            if not covered_subjects:
                st.info("You haven't covered enough topics yet. Try some topic-specific tests below to build your profile!")
            else:
                for subject in covered_subjects:
                    with st.container(border=True):
                        st.subheader(f"Subject: {subject}")
                        weak_topics_list = get_weakest_topics(performance_data, subject, count=3)
                        if weak_topics_list:
                            st.write(f"This test will focus on: *{', '.join(weak_topics_list)}*")
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            q_count = st.slider(f"Number of Questions for {subject}", 5, 20, 10, key=f"q_{subject}")
                        with col2:
                            st.write("") 
                            st.write("") 
                            if st.button("Start Adaptive Test", key=f"start_comp_{subject}"):
                                start_test(
                                    subject=subject,
                                    q_count=q_count,
                                    weak_topics=weak_topics_list,
                                    focus_topic=None
                                )

            # --- Optional Topic-wise Tests ---
            st.markdown("---")
            st.header("Chapter Tests")
            st.write("Practice specific topics you have already studied.")

            for subject, topics in performance_data.items():
                with st.expander(f"**{subject}** - Topics"):
                    for topic in topics:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"- **{topic}**")
                        with col2:
                            if st.button("Practice", key=f"start_opt_{subject}_{topic}"):
                                start_test(
                                    subject=subject,
                                    q_count=5, # Fixed for topic tests
                                    weak_topics=None,
                                    focus_topic=topic
                                )
        # --- The rest of your tab1 code (quiz active/complete modes) remains unchanged ---
        elif st.session_state.quiz_mode == "active" and st.session_state.current_test:
            idx = st.session_state.current_question_index
            if idx >= len(st.session_state.current_test):
                st.session_state.quiz_mode = "complete"
                st.rerun()
                
            question = st.session_state.current_test[idx]
            
            with st.container(border=True):
                    st.subheader(f"Question {idx + 1}/{len(st.session_state.current_test)}")
                    st.write(f"**Topic:** {question.get('topic', 'General')} | **Difficulty:** {question.get('difficulty', 'Medium')}")
                    st.markdown(f"### {question['question_text']}")

                    options = question['distractors'] + [question['answer']]
                    # Shuffle options only once per question
                    if f"options_{idx}" not in st.session_state:
                        random.shuffle(options)
                        st.session_state[f"options_{idx}"] = options

                    user_choice = st.radio("Select your answer:", st.session_state[f"options_{idx}"], key=f"quiz_{idx}", index=None)

                    if st.button("Submit Answer", key=f"submit_{idx}"):
                        if user_choice is None:
                            st.warning("Please select an answer!")
                        else:
                            is_correct = (user_choice == question['answer'])
                            
                            st.session_state.test_results.append({
                                "question": question['question_text'],
                                "topic": question.get('topic', 'General'),
                                "user_answer": user_choice,
                                "correct_answer": question['answer'],
                                "is_correct": is_correct,
                                "explanation": question.get('explanation', 'No explanation available.') # <-- ADD THIS LINE
                            })
                            
                            
                            updated_user_profile = profile_manager.log_quiz_result(
                                profile=st.session_state.user_profile,  # Pass the ENTIRE user profile
                                subject=st.session_state.current_subject,
                                topic=question['topic'],
                                is_correct=is_correct
                            )
                            # Save the updated full profile back to the session state
                            st.session_state.user_profile = updated_user_profile
                            # Also, refresh the performance_profile shortcut to ensure it has the latest data
                            st.session_state.performance_profile = updated_user_profile.get('performance_data_per_subject', {})

                            if is_correct:
                                st.success("Correct! Well done! ✅")
                            else:
                                st.error(f"Not quite. The correct answer was: **{question['answer']}** ❌")

                            time.sleep(1.5)
                            st.session_state.current_question_index += 1
                            # Clean up old options from session_state
                            if f"options_{idx}" in st.session_state:
                                del st.session_state[f"options_{idx}"]
                            st.rerun()

            # --- Quiz Completion Screen ---    
        elif st.session_state.quiz_mode == "complete":
            
            # --- ADD THIS BLOCK to log the test event ---
            if not st.session_state.get('test_event_logged', False):
                test_summary = {
                    "timestamp": datetime.now().isoformat() + "Z",
                    "subject": st.session_state.current_subject,
                    "score": sum(1 for r in st.session_state.test_results if r['is_correct']),
                    "total_questions": len(st.session_state.test_results),
                    "type": "Topic Test" if st.session_state.get('focus_topic') else "Subject Test",
                    "topic": st.session_state.get('focus_topic')
                }
                st.session_state.user_profile.setdefault("test_history", []).append(test_summary)
                st.session_state.test_event_logged = True
            
            # Add a flag to ensure we only save once per completed quiz
            if not st.session_state.get('results_saved', False):
                with st.spinner("Saving your progress..."):
                    save_student_data(st.session_state.user_profile)
                    st.session_state.results_saved = True

            # st.balloons()
            st.success("🎉 Quiz complete! Your performance has been recorded and saved.")
            
            st.subheader("Test Result Summary")

            # Calculate and display score
            if st.session_state.get('test_results'):
                correct_answers = sum(1 for result in st.session_state.test_results if result['is_correct'])
                total_questions = len(st.session_state.test_results)
                st.metric("Your Score", f"{correct_answers} / {total_questions}")

                st.markdown("---")
                st.subheader("Detailed Review")

                for i, result in enumerate(st.session_state.test_results):
                    with st.container(border=True):
                        st.write(f"**Question {i+1}:** {result['question']}")
                        st.write(f"**Topic:** {result['topic']}")
                        if result['is_correct']:
                            st.success(f"Your answer: {result['user_answer']} ✅")
                        else:
                            st.error(f"Your answer: {result['user_answer']} ❌")
                            st.info(f"Correct answer: {result['correct_answer']}")
                            with st.expander("View Solution"):
                                st.markdown(result['explanation'])
            
            st.info("Check the 'Analytics Dashboard' tab to see your updated progress.")

            if st.button("Take Another Test"):
                st.session_state.quiz_mode = "setup"
                st.session_state.current_test = None
                st.session_state.current_question_index = 0
                st.session_state.results_saved = False # Reset flag for the next quiz
                st.rerun()
            
    with tab2:
        st.header("Your Performance Dashboard")
        
        # st.subheader("Debug View: Current Performance Data")
        # st.json(st.session_state.get('performance_profile', {}))

        if not st.session_state.user_profile or not st.session_state.performance_profile:
            st.info("Your dashboard is empty. Complete a quiz in the 'Generate Test' tab to see your progress!")
        else:
            performance_profile = st.session_state.performance_profile
            subjects_available = list(performance_profile.keys())

            if not subjects_available:
                st.info("No performance data found. Complete a quiz to get started!")
            else:
                selected_subject = st.selectbox(
                    "Select a subject to view analytics",
                    options=subjects_available,
                    key="analytics_subject"
                )

                st.subheader(f"Showing Analytics for: **{selected_subject}**")
                metrics = analytics.calculate_metrics(st.session_state.user_profile, selected_subject)

                if not metrics.get('performance_by_topic'):
                    st.warning(f"No data found for '{selected_subject}'.")
                else:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Average Accuracy", f"{metrics.get('average_accuracy', 0.0):.1f}%")
                    col2.metric("Topics Practiced", len(metrics.get('performance_by_topic', {})))
                    col3.metric("Total Questions", metrics.get('total_questions_answered', 0))
                    
                    # In tab2, after the columns for the main metrics
                st.divider()
                st.subheader("Test History")

                test_history = st.session_state.user_profile.get("test_history", [])
                subject_history = [t for t in test_history if t['subject'] == selected_subject]

                if not subject_history:
                    st.info(f"No tests have been completed for {selected_subject} yet.")
                else:
                    subject_tests = [t for t in subject_history if t['type'] == 'Subject Test']
                    topic_tests = [t for t in subject_history if t['type'] == 'Topic Test']

                    col1, col2 = st.columns(2)
                    col1.metric("Subject Tests Taken", len(subject_tests))
                    col2.metric("Topic Tests Taken", len(topic_tests))

                    st.write("Recent Test Scores:")
                    for test in reversed(subject_history[-3:]):
                        test_type_str = f"({test['topic']})" if test['type'] == 'Topic Test' and test['topic'] else ""
                        st.info(f"**{test['type']} {test_type_str}**: Scored {test['score']}/{test['total_questions']} on {pd.to_datetime(test['timestamp']).strftime('%d-%b-%Y')}")


                    st.subheader("Performance Breakdown by Topic")
                    topic_df = pd.DataFrame(
                        list(metrics['performance_by_topic'].items()),
                        columns=['Topic', 'Accuracy']
                    ).sort_values("Accuracy", ascending=True) # Sort ascending to show weakest first
                    
                    chart = alt.Chart(topic_df).mark_bar().encode(
                        x=alt.X('Accuracy:Q', title='Accuracy (%)', scale=alt.Scale(domain=[0, 100])),
                        y=alt.Y('Topic:N', sort='-x', title='Topic'),
                        color=alt.Color('Accuracy:Q',
                        legend=None,
                        scale=alt.Scale(
                            # Define the thresholds for color changes
                            domain=[50, 75],
                            # Define the colors for ranges: <50, 50-75, >75
                            range=['tomato', 'orange', 'mediumseagreen']
                        )
                    ),
                        tooltip=['Topic', 'Accuracy']
                    ).properties(
                        title='Your Accuracy by Topic'
                    )
                    st.altair_chart(chart, use_container_width=True)

