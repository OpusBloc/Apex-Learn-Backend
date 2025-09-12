import json
from datetime import datetime
import pandas as pd
from typing import Dict, Any

def calculate_metrics(profile: dict, subject: str) -> dict:
    """
    Calculates key performance indicators (KPIs) from the user's profile data.
    """
    if not profile or not profile.get("performance_log"):
        return {
            "streak_days": 0, "average_accuracy": 0, "topics_covered_percent": 0,
            "hours_spent": 0, "performance_by_topic": {}
        }

    log_df = pd.DataFrame(profile["performance_log"])
    #log_df['timestamp'] = pd.to_datetime(log_df['timestamp'])
    log_df['timestamp'] = pd.to_datetime(log_df['timestamp'], format='ISO8601')
    log_df['date'] = log_df['timestamp'].dt.date

    # --- Streak Calculation (no change needed) ---
    dates = sorted(log_df['date'].unique())
    streak = 0
    if dates:
        streak = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                streak += 1
            else:
                streak = 1

    # --- Subject-Specific Metrics ---
    subject_df = log_df[log_df['subject'] == subject]
    avg_accuracy = 0
    performance_by_topic = {}

    if not subject_df.empty:
        avg_accuracy = (subject_df['is_correct'].sum() / len(subject_df)) * 100

    # --- Performance by Topic (This is the key change) ---
    topic_stats = profile.get("performance_data_per_subject", {}).get(subject, {})
    for topic, data in topic_stats.items():
        if data.get('total', 0) > 0:
            accuracy = (data['correct'] / data['total']) * 100
            performance_by_topic[topic] = round(accuracy, 2)

    hours_spent = len(dates) * (5 / 60)
    total_syllabus_topics = 20 # Placeholder for total topics
    topics_covered_percent = (len(performance_by_topic) / total_syllabus_topics) * 100

    return {
        "streak_days": streak,
        "average_accuracy": round(avg_accuracy, 2),
        "topics_covered_percent": round(topics_covered_percent, 2),
        "hours_spent": round(hours_spent, 2),
        "performance_by_topic": performance_by_topic
    }

# The `predict_readiness_with_llm` function does not need any changes.
def predict_readiness_with_llm(
    metrics: Dict[str, Any],
    profile: Dict[str, Any],
    subject: str,
    llm
) -> Dict[str, Any]:
    """
    Uses an LLM to generate a qualitative analysis and readiness forecast.
    """
    performance_summary = json.dumps(metrics['performance_by_topic'], indent=2)
    prompt = f"""
    You are an expert AI academic coach. Analyze the following student performance data for the subject '{subject}'
    and provide a readiness forecast.

    Student's Goal:
    - Target Score: {profile.get('target_score', 85)}%
    - Exam Date: {profile.get('exam_date', 'Not set')}

    Quantitative Metrics:
    - Study Streak: {metrics['streak_days']} days
    - Average Accuracy: {metrics['average_accuracy']}%
    - Syllabus Coverage (estimated): {metrics['topics_covered_percent']}%
    - Performance by Topic:
    {performance_summary}

    Based on this data, provide your analysis in a structured JSON format. The JSON object must have the following keys:
    - "predicted_score": Your integer prediction of the student's likely score if the exam were today.
    - "confidence_level": Your confidence in this prediction ('Low', 'Medium', 'High').
    - "key_observations": A list of 2-3 bullet points highlighting strengths or positive trends.
    - "key_risks": A list of 2-3 bullet points identifying weaknesses, inconsistencies, or risks.
    - "recommendations": A list of 2-3 actionable, personalized recommendations for the student to improve.

    Respond ONLY with the raw JSON object, without any introductory text or code blocks.
    """

    try:
        response = llm.complete(prompt)
        cleaned_response = str(response).strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing LLM response for readiness: {e}")
        return {
            "predicted_score": 60,
            "confidence_level": "Low",
            "key_observations": ["Analysis could not be generated due to an error."],
            "key_risks": ["Please try again later."],
            "recommendations": ["Ensure the AI model is accessible and returning valid JSON."]
        }