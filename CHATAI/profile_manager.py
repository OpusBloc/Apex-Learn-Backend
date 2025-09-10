import json
import os
from datetime import datetime

PROFILE_FILE = "user_profile.json"

def load_profile() -> dict:
    """
    Loads the user profile from the JSON file.
    If the file doesn't exist, it creates a default profile based on the new structure.
    """
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r') as f:
            return json.load(f)
    else:
        # Create a default structure matching your detailed example
        return {
            "user_id": "new_student",
            "board": None,
            "class": None,
            "target_score": 85,
            "exam_date": None,
            "study_sessions": [],
            "performance_log": [],
            "performance_data_per_subject": {}
        }

def save_profile(profile: dict):
    """Saves the provided profile dictionary to the JSON file."""
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profile, f, indent=4)

def log_quiz_result(profile: dict, subject: str, topic: str, is_correct: bool) -> dict:
    """
    Logs a quiz result to the performance_log and updates the aggregated
    stats in performance_data_per_subject.
    """
    # 1. Add to the detailed performance log
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "subject": subject,
        "topic": topic,
        "is_correct": is_correct
    }
    profile["performance_log"].append(log_entry)

    # 2. Update the aggregated stats in the nested dictionary
    #    (This is the key change)
    if subject not in profile["performance_data_per_subject"]:
        profile["performance_data_per_subject"][subject] = {}

    if topic not in profile["performance_data_per_subject"][subject]:
        profile["performance_data_per_subject"][subject][topic] = {"correct": 0, "total": 0}

    profile["performance_data_per_subject"][subject][topic]["total"] += 1
    if is_correct:
        profile["performance_data_per_subject"][subject][topic]["correct"] += 1

    # 3. Save the updated profile
    save_profile(profile)
    return profile