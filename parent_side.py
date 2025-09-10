import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import datetime
import json
import logging
from datetime import timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(page_title="Parent Dashboard - Study Plan", layout="wide")

# Initialize session state for shared data
if "study_plan" not in st.session_state:
    st.session_state.study_plan = {}
if "completed_tasks" not in st.session_state:
    st.session_state.completed_tasks = 0
if "total_tasks" not in st.session_state:
    st.session_state.total_tasks = 0
if "weak_topics" not in st.session_state:
    st.session_state.weak_topics = []
if "knowledge_level" not in st.session_state:
    st.session_state.knowledge_level = "beginner"
if "board" not in st.session_state:
    st.session_state.board = None
if "class_num" not in st.session_state:
    st.session_state.class_num = None
if "subject" not in st.session_state:
    st.session_state.subject = None
if "quiz" not in st.session_state:
    st.session_state.quiz = []

# Dummy data for session state
st.session_state.study_plan = {
    "Week 1": [
        {"date": "2025-08-20", "topic": "Algebra", "time": 2.0, "completed": True},
        {"date": "2025-08-21", "topic": "Geometry", "time": 1.5, "completed": False},
        {"date": "2025-08-22", "topic": "Trigonometry", "time": 1.0, "completed": True},
    ],
    "Week 2": [
        {"date": "2025-08-27", "topic": "Algebra", "time": 2.0, "completed": False},
        {"date": "2025-08-28", "topic": "Calculus", "time": 2.5, "completed": False},
        {"date": "2025-08-29", "topic": "Geometry", "time": 1.5, "completed": True},
    ],
    "Week 3": [
        {"date": "2025-09-01", "topic": "Trigonometry", "time": 1.5, "completed": False},
        {"date": "2025-09-02", "topic": "Calculus", "time": 2.0, "completed": False},
    ]
}
st.session_state.completed_tasks = 3
st.session_state.total_tasks = 8
st.session_state.weak_topics = ["Calculus", "Trigonometry"]
st.session_state.knowledge_level = "intermediate"
st.session_state.board = "CBSE"
st.session_state.class_num = 10
st.session_state.subject = "Mathematics"
st.session_state.quiz = [
    {"topic": "Algebra", "score": 80},
    {"topic": "Geometry", "score": 65},
    {"topic": "Trigonometry", "score": 50},
    {"topic": "Calculus", "score": 40}
]

# Helper functions
def calculate_progress_metrics():
    """Calculate progress metrics for the student."""
    completed_tasks = st.session_state.completed_tasks
    total_tasks = st.session_state.total_tasks
    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
    missed_tasks = sum(1 for tasks in st.session_state.study_plan.values() for task in tasks if not task["completed"] and datetime.datetime.strptime(task["date"], "%Y-%m-%d") < datetime.datetime.now())
    
    # Calculate topic-specific progress
    topic_progress = {}
    for week, tasks in st.session_state.study_plan.items():
        for task in tasks:
            topic = task["topic"]
            if topic not in topic_progress:
                topic_progress[topic] = {"completed": 0, "total": 0}
            topic_progress[topic]["total"] += 1
            if task["completed"]:
                topic_progress[topic]["completed"] += 1
    
    # Calculate progress percentages
    topic_percentages = {
        topic: (data["completed"] / data["total"] * 100) if data["total"] > 0 else 0
        for topic, data in topic_progress.items()
    }
    
    return {
        "completion_rate": completion_rate * 100,
        "missed_tasks": missed_tasks,
        "topic_progress": topic_percentages
    }

def generate_progress_summary():
    """Generate an AI-written progress summary."""
    metrics = calculate_progress_metrics()
    completion_rate = metrics["completion_rate"]
    missed_tasks = metrics["missed_tasks"]
    topic_progress = metrics["topic_progress"]
    
    summary = f"""
Your child is making strides in their {st.session_state.subject} journey for Class {st.session_state.class_num} ({st.session_state.board})! 
They've completed {metrics['completion_rate']:.1f}% of their assigned quests, showing dedication to mastering the syllabus. 
"""
    if topic_progress:
        top_topic = max(topic_progress, key=topic_progress.get)
        top_progress = topic_progress[top_topic]
        summary += f"Notably, they've excelled in '{top_topic}' with a {top_progress:.1f}% completion rate, a true victory in this territory! "
    if missed_tasks > 0:
        summary += f"However, {missed_tasks} quest(s) were missed, which we can reschedule to keep them on track. "
    summary += "Keep supporting their learning adventure!"
    
    return summary

def detect_risks():
    """Detect if the student is falling behind."""
    metrics = calculate_progress_metrics()
    completion_rate = metrics["completion_rate"]
    missed_tasks = metrics["missed_tasks"]
    
    risks = []
    if completion_rate < 50:
        risks.append("Low completion rate: Your child has completed less than 50% of their tasks, indicating a risk of falling behind.")
    if missed_tasks >= 3:
        risks.append(f"Missed tasks: {missed_tasks} tasks are overdue, which may impact their progress.")
    
    for topic, progress in metrics["topic_progress"].items():
        if progress < 30 and topic in st.session_state.weak_topics:
            risks.append(f"Struggling in weak topic: Only {progress:.1f}% progress in '{topic}', a known weak area.")
    
    return risks if risks else ["No immediate risks detected. Your child is progressing steadily!"]

def recommend_focus_topics():
    """Recommend focus topics for the upcoming week."""
    metrics = calculate_progress_metrics()
    topic_progress = metrics["topic_progress"]
    weak_topics = st.session_state.weak_topics
    
    # Prioritize weak topics with low progress
    focus_topics = [
        topic for topic, progress in topic_progress.items()
        if topic in weak_topics and progress < 70
    ]
    
    # If fewer than 3 topics, add other low-progress topics
    if len(focus_topics) < 3:
        additional_topics = [
            topic for topic, progress in sorted(topic_progress.items(), key=lambda x: x[1])
            if topic not in focus_topics and progress < 70
        ]
        focus_topics.extend(additional_topics[:3 - len(focus_topics)])
    
    if not focus_topics:
        focus_topics = weak_topics[:3] if len(weak_topics) >= 3 else weak_topics
    
    return focus_topics if focus_topics else ["Continue reinforcing all topics evenly."]

def generate_progress_plot():
    """Generate a bar plot of topic progress."""
    metrics = calculate_progress_metrics()
    topic_progress = metrics["topic_progress"]
    
    if not topic_progress:
        return None
    
    df = pd.DataFrame({
        "Topic": list(topic_progress.keys()),
        "Progress (%)": list(topic_progress.values())
    })
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x="Progress (%)", y="Topic", hue="Topic", data=df, palette="viridis", legend=False)
    plt.title("Progress by Topic")
    plt.xlabel("Completion Percentage")
    plt.ylabel("Topic")
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return buf

def get_download_link(buf, filename):
    """Generate a download link for the plot."""
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">Download Progress Chart</a>'
    return href

# Parent Dashboard UI
st.title("Parent Dashboard: Your Child's Learning Adventure")
st.write(f"Welcome, Guardian! Monitor your child's progress in {st.session_state.subject} for Class {st.session_state.class_num} ({st.session_state.board}). Get insights, track risks, and receive tailored recommendations to support their quest!")

if not st.session_state.study_plan:
    st.warning("No study plan data available. Please ensure your child has created a study plan.")
else:
    # Progress Summary
    st.subheader("Progress Summary")
    summary = generate_progress_summary()
    st.markdown(summary)
    
    # Progress Visualization
    st.subheader("Progress by Topic")
    plot_buf = generate_progress_plot()
    if plot_buf:
        st.image(plot_buf, caption="Topic Progress Chart", use_column_width=True)
        st.markdown(get_download_link(plot_buf, "progress_chart.png"), unsafe_allow_html=True)
    else:
        st.write("No progress data available for visualization.")
    
    # Risk Detection
    st.subheader("Risk Detection")
    risks = detect_risks()
    for risk in risks:
        st.warning(risk)
    
    # Recommendations
    st.subheader("Recommended Focus Topics for This Week")
    focus_topics = recommend_focus_topics()
    if isinstance(focus_topics, list) and focus_topics and not isinstance(focus_topics[0], str):
        st.error("Invalid focus topics format.")
        focus_topics = ["Unable to generate recommendations at this time."]
    for topic in focus_topics:
        st.markdown(f"- {topic}")
    
    # Detailed Study Plan View
    st.subheader("Detailed Study Plan")
    for week, tasks in st.session_state.study_plan.items():
        with st.expander(f"Week {week.split()[1]}"):
            for task in tasks:
                status = "✅ Conquered" if task["completed"] else "⏳ Pending"
                overdue = datetime.datetime.strptime(task["date"], "%Y-%m-%d") < datetime.datetime.now() and not task["completed"]
                status = "⚠️ Overdue" if overdue else status
                st.markdown(f"**Date**: {task['date']} | **Topic**: {task['topic']} | **Time**: {task['time']} hours | **Status**: {status}")
    
    # Parental Notifications
    st.subheader("Notifications")
    missed_tasks = sum(1 for tasks in st.session_state.study_plan.values() for task in tasks if not task["completed"] and datetime.datetime.strptime(task["date"], "%Y-%m-%d") < datetime.datetime.now())
    if missed_tasks > 0:
        st.warning(f"Your child has {missed_tasks} overdue tasks. Consider discussing their schedule or rescheduling these tasks in their student dashboard.")
    else:
        st.success("Your child is on track with no overdue tasks!")
    
    # Additional Feature: Progress Report Download
    st.subheader("Download Progress Report")
    if st.button("Generate PDF Report"):
        try:
            from fpdf import FPDF
            
            class PDF(FPDF):
                def header(self):
                    self.set_font("Arial", "B", 12)
                    self.cell(0, 10, f"Progress Report: {st.session_state.subject} - Class {st.session_state.class_num} ({st.session_state.board})", 0, 1, "C")
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", "I", 8)
                    self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")
            
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Summary
            pdf.cell(0, 10, "Progress Summary", 0, 1, "L")
            pdf.multi_cell(0, 10, summary)
            pdf.ln(10)
            
            # Risks
            pdf.cell(0, 10, "Risks Detected", 0, 1, "L")
            for risk in risks:
                pdf.multi_cell(0, 10, f"- {risk}")
            pdf.ln(10)
            
            # Recommendations
            pdf.cell(0, 10, "Recommended Focus Topics", 0, 1, "L")
            for topic in focus_topics:
                pdf.multi_cell(0, 10, f"- {topic}")
            
            # Save PDF
            pdf_buffer = BytesIO()
            pdf_output = pdf.output(dest="S").encode("latin1")
            pdf_buffer.write(pdf_output)
            pdf_buffer.seek(0)
            
            st.download_button(
                label="Download PDF Report",
                data=pdf_buffer,
                file_name="progress_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            st.error("Failed to generate PDF report. Please try again.")
    
    # Additional Feature: Parental Guidance Tips
    st.subheader("Parental Guidance Tips")
    st.markdown("""
    - **Encourage Consistency**: Set a regular study time to help your child stay on track.
    - **Celebrate Wins**: Acknowledge completed quests to boost motivation.
    - **Discuss Challenges**: Talk about weak topics to understand their struggles.
    - **Monitor Regularly**: Check this dashboard weekly to stay updated.
    """)