import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ----------------------------
# Helpers for summary filenames
# ----------------------------
def current_summary_filename() -> str:
    now = datetime.now()
    mm = now.strftime("%m")   # '12'
    yyyy = now.strftime("%Y") # '2025'
    return f"summary{mm}{yyyy}.json"


def list_summary_files_newest_first(user_dir):
    files = [
        f for f in os.listdir(user_dir)
        if f.startswith("summary") and f.endswith(".json")
    ]

    def sort_key(name: str):
        core = name[len("summary"):-len(".json")]  # '122025'
        if len(core) != 6:
            return (0, 0)
        mm = core[:2]
        yyyy = core[2:]
        try:
            return (int(yyyy), int(mm))
        except ValueError:
            return (0, 0)

    return sorted(files, key=sort_key, reverse=True)


# ----------------------------
# Summary load & search
# ----------------------------
def load_summaries_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def find_best_session_for_query_in_file(summary_path, query: str):
    summaries = load_summaries_from_file(summary_path)
    print(f"[DEBUG] Loaded {len(summaries)} summaries from {summary_path}")
    if not summaries or not query.strip():
        return None

    q = query.lower()
    words = [w for w in q.split() if len(w) > 2]

    best = None
    best_score = 0

    for item in summaries:
        text = str(item.get("summary", "")).lower()
        score = sum(1 for w in words if w in text)
        if score > best_score:
            best_score = score
            best = item

    return best if best_score > 0 else None


def find_best_session_across_months(user_dir, query: str):
    print(f"[DEBUG] Searching summaries for query: {query!r}")
    for fname in list_summary_files_newest_first(user_dir):
        path = os.path.join(user_dir, fname)
        print(f"[DEBUG] Checking summary file: {path}")
        best = find_best_session_for_query_in_file(path, query)
        if best is not None:
            print(f"[DEBUG] Found match in {fname}: {best}")
            return best
    print("[DEBUG] No matching session found in any summary file.")
    return None


# ----------------------------
# Test data setup
# ----------------------------
def ensure_test_user_summaries(user_dir):
    os.makedirs(user_dir, exist_ok=True)

    # Create two fake monthly summary files for testing
    # summary112025.json (older)
    old_name = "summary112025.json"
    old_path = os.path.join(user_dir, old_name)
    if not os.path.exists(old_path):
        old_data = [
            {
                "session_id": "2025-11-10T10:00:00",
                "timestamp": "2025-11-10T10:00:00",
                "summary": "general chat, greetings, small talk"
            },
            {
                "session_id": "2025-11-15T14:30:00",
                "timestamp": "2025-11-15T14:30:00",
                "summary": "bible study, personal reflection"
            }
        ]
        with open(old_path, "w", encoding="utf-8") as f:
            json.dump(old_data, f, ensure_ascii=False, indent=2)
        print(f"[SETUP] Wrote fake {old_name}")

    # summary122025.json (newer)
    new_name = "summary122025.json"
    new_path = os.path.join(user_dir, new_name)
    if not os.path.exists(new_path):
        new_data = [
            {
                "session_id": "2025-12-11T21:52:05",
                "timestamp": "2025-12-11T21:52:05",
                "summary": "openai residency, github portfolio, holly assistant, ollama setup"
            },
            {
                "session_id": "2025-12-12T08:30:00",
                "timestamp": "2025-12-12T08:30:00",
                "summary": "voice assistant, tts models, xtts, piper"
            }
        ]
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print(f"[SETUP] Wrote fake {new_name}")


# ----------------------------
# Main test flow
# ----------------------------
def main():
    # Simulate one user folder like your real code
    user_dir = os.path.join(BASE_DIR, "test_user_summaries")
    ensure_test_user_summaries(user_dir)

    print("\n--- Summary files present (newest first) ---")
    for f in list_summary_files_newest_first(user_dir):
        print(" ", f)

    while True:
        query = input("\nType a topic to search summaries (or 'exit'): ")
        if query.strip().lower() == "exit":
            break

        best = find_best_session_across_months(user_dir, query)
        if best is None:
            print("No matching past session found.")
        else:
            print("\nBest match:")
            print(json.dumps(best, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
