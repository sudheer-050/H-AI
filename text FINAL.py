import subprocess
import sys
import random
import os
import json
from datetime import datetime

# ----------------------------
# Ollama import / install
# ----------------------------
try:
    import ollama
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ollama"])
    import ollama  # type: ignore

# ----------------------------
# Model & system prompt
# ----------------------------
MODEL = "llama3"  # Make sure you've run: ollama pull llama3

SYSTEM_PROMPT = (
    "You are H, a warm, human-like assistant talking to Sudheer and people he cares about. "
    "Reply like a normal person in 1–2 short sentences. "
    "Be natural and conversational, not formal. "
    "Avoid repeating your identity or giving long explanations. "
    "Only mention that you are an AI if the user directly asks what you are."
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, "users")

# ----------------------------
# Helpers for dates / filenames
# ----------------------------
def current_summary_filename() -> str:
    """Return current month summary file name like summary122025.json."""
    now = datetime.now()
    mm = now.strftime("%m")
    yyyy = now.strftime("%Y")
    return f"summary{mm}{yyyy}.json"

# ----------------------------
# User / folder helpers
# ----------------------------
def sanitize_name(name: str) -> str:
    cleaned = "".join(c for c in name.strip() if c.isalnum() or c in (" ", "_", "-"))
    return cleaned.replace(" ", "-")

def find_user_folder_by_id(user_id: str):
    if not os.path.isdir(USERS_DIR):
        return None
    for entry in os.listdir(USERS_DIR):
        full = os.path.join(USERS_DIR, entry)
        if os.path.isdir(full) and entry.startswith(f"{user_id}-"):
            return full
    return None

def ask_for_new_5_digit_id() -> str:
    """Ask the new user to create a unique 5-digit ID."""
    while True:
        candidate = input("Create a 5-digit ID for yourself (numbers only): ").strip()
        if len(candidate) != 5 or not candidate.isdigit():
            print("Please enter exactly 5 digits, e.g., 12345.")
            continue

        existing = find_user_folder_by_id(candidate)
        if existing is not None:
            print("That ID is already in use. Please choose a different 5-digit ID.")
            continue

        return candidate

def create_new_user_folder(user_id: str, name: str, relationship: str) -> str:
    safe_name = sanitize_name(name)
    folder_name = f"{user_id}-{safe_name}"
    user_dir = os.path.join(USERS_DIR, folder_name)

    os.makedirs(user_dir, exist_ok=True)
    sessions_dir = os.path.join(user_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    # Create current month summary file if missing
    summary_name = current_summary_filename()
    summary_path = os.path.join(user_dir, summary_name)
    if not os.path.exists(summary_path):
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    profile_path = os.path.join(user_dir, "profile.json")
    profile = {
        "id": user_id,
        "name": name,
        "relationship_with_sudheer": relationship,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    return user_dir

def ensure_existing_user_dirs(user_dir: str):
    sessions_dir = os.path.join(user_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    # Ensure current month summary file exists
    summary_name = current_summary_filename()
    summary_path = os.path.join(user_dir, summary_name)
    if not os.path.exists(summary_path):
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    return sessions_dir

def prompt_for_user():
    """
    Ask for user identity.
    NEW: user types 'new' -> chooses fresh 5-digit ID, then name + relationship.
    EXISTING: user types their existing 5-digit ID.
    """
    os.makedirs(USERS_DIR, exist_ok=True)

    print("Before we start, please identify yourself.")
    status = input(
        "If you're NEW, type 'new'.\n"
        "If you've used H before, type your 5-digit ID: "
    ).strip().lower()

    if status == "new":
        user_id = ask_for_new_5_digit_id()
        name = input("What's your name? ").strip()
        relationship = input("What's your relationship with Sudheer? ").strip()
        user_dir = create_new_user_folder(user_id, name, relationship)
    else:
        # Treat input as existing ID
        user_id = status
        user_dir = find_user_folder_by_id(user_id)
        if user_dir is None:
            print("\nNo existing user found with that ID. Let's register you as new.")
            user_id = ask_for_new_5_digit_id()
            name = input("What's your name? ").strip()
            relationship = input("What's your relationship with Sudheer? ").strip()
            user_dir = create_new_user_folder(user_id, name, relationship)

    sessions_dir = ensure_existing_user_dirs(user_dir)
    return user_dir, sessions_dir

# ----------------------------
# Summarization helpers (monthly files)
# ----------------------------
def build_session_summary_text(session_messages):
    """
    Use the LLM to generate keyword-style tags for the conversation.
    """
    if not isinstance(session_messages, list):
        return "general"

    lines = []
    for m in session_messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "user")
        content = str(m.get("content", ""))
        if not content.strip():
            continue
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"H: {content}")

    transcript = "\n".join(lines)
    if not transcript.strip():
        return "general"

    prompt = (
        "From the following conversation between a user and an AI assistant named H, "
        "extract 8–20 short keywords or key phrases that capture:\n"
        "- main topics and projects\n"
        "- important tasks, goals and plans\n"
        "- trips and places\n"
        "- people and relationships\n"
        "- strong emotions and preferences.\n"
        "Think like a memory system: anything the user would want H to remember later "
        "for future conversations should become a keyword or short phrase.\n"
        "Respond ONLY with comma-separated keywords or short phrases, no explanations.\n\n"
        f"{transcript}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract important memory-style keywords from conversations. "
                    "Return only comma-separated keywords or short phrases."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    text = response["message"]["content"]
    return text.strip() if isinstance(text, str) else "general"

def save_session_and_summary(
    user_dir,
    sessions_dir,
    session_id,
    session_messages,
):
    """
    Save full session and append a keyword-style summary entry
    into the current month summary file (summaryMMYYYY.json).
    """
    file_friendly_id = session_id.replace(":", "-")
    session_path = os.path.join(sessions_dir, f"session_{file_friendly_id}.json")
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_messages, f, ensure_ascii=False, indent=2)

    try:
        summary_text = build_session_summary_text(session_messages)
    except Exception as e:
        summary_text = f"[Summary generation failed inside code: {e}]"

    summary_item = {
        "session_id": session_id,
        "timestamp": session_id,
        "summary": summary_text,
    }

    summary_name = current_summary_filename()
    summary_path = os.path.join(user_dir, summary_name)

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            summaries = json.load(f)
            if not isinstance(summaries, list):
                summaries = []
    except (FileNotFoundError, json.JSONDecodeError):
        summaries = []

    summaries.append(summary_item)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

# ----------------------------
# Retrieval helpers (monthly, newest -> oldest)
# ----------------------------
def list_summary_files_newest_first(user_dir):
    files = [
        f for f in os.listdir(user_dir)
        if f.startswith("summary") and f.endswith(".json")
    ]

    def sort_key(name: str):
        core = name[len("summary"):-len(".json")]  # e.g. '122025'
        if len(core) != 6:
            return (0, 0)
        mm = core[:2]
        yyyy = core[2:]
        try:
            return (int(yyyy), int(mm))
        except ValueError:
            return (0, 0)

    return sorted(files, key=sort_key, reverse=True)

def load_summaries_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def find_best_session_for_query_in_file(summary_path, query: str):
    summaries = load_summaries_from_file(summary_path)
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
    for fname in list_summary_files_newest_first(user_dir):
        path = os.path.join(user_dir, fname)
        best = find_best_session_for_query_in_file(path, query)
        if best is not None:
            return best
    return None

def load_session_messages_by_id(sessions_dir, session_id: str):
    file_friendly_id = session_id.replace(":", "-")
    path = os.path.join(sessions_dir, f"session_{file_friendly_id}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# ----------------------------
# Background memory builder
# ----------------------------
def build_memory_background(user_dir, sessions_dir, query: str, max_keywords: int = 25) -> str:
    """
    Build a short background memory paragraph from summaries and
    the best matching past session, so H can remember older topics.
    """
    parts = []

    # 1) Latest monthly summary (high-level topics)
    summary_files = list_summary_files_newest_first(user_dir)
    if summary_files:
        latest_path = os.path.join(user_dir, summary_files[0])
        summaries = load_summaries_from_file(latest_path)
        recent_summaries = [
            str(item.get("summary", "")) for item in summaries[-5:]
            if isinstance(item, dict)
        ]
        if recent_summaries:
            joined = ", ".join(recent_summaries)
            tokens = [t.strip() for t in joined.split(",") if t.strip()]
            if len(tokens) > max_keywords:
                tokens = tokens[-max_keywords:]
            parts.append(
                "Important past topics and memories: " + ", ".join(tokens)
            )

    # 2) Best matching past session for this query
    best = find_best_session_across_months(user_dir, query)
    if best is not None:
        past_session_id = best.get("session_id")
        past_messages = load_session_messages_by_id(sessions_dir, past_session_id)
        trimmed_past = [
            m for m in past_messages
            if isinstance(m, dict) and m.get("role") in {"user", "assistant"}
        ][-10:]  # last 10 turns

        if trimmed_past:
            lines = []
            for m in trimmed_past:
                role = m.get("role")
                content = str(m.get("content", "")).strip()
                if not content:
                    continue
                prefix = "User:" if role == "user" else "H:"
                lines.append(f"{prefix} {content}")
            past_block = "\n".join(lines)
            parts.append(
                "Relevant excerpt from a previous conversation with this user:\n"
                + past_block
            )

    if not parts:
        return ""

    return (
        "Background memory about this user from past conversations.\n"
        "Use this to stay consistent with their life, projects, preferences, and plans, "
        "but do NOT repeat it back verbatim:\n\n"
        + "\n\n".join(parts)
    )

# ----------------------------
# Replies for empty input
# ----------------------------
empty_replies = [
    "Are you kidding me? You sent nothing!",
    "Huh? Cat got your keyboard?",
    "I can't read minds... yet!",
    "Are you feeling OK, or just messing with me?",
    "You ghosted me! Try again?",
    "Nothing there—I hope that's not a riddle!",
    "Come on, don’t leave me hanging!",
    "Oops, did you forget to type something?",
    "Blank messages...?, very mysterious!",
    "Did your keyboard run out of words?",
]

# ----------------------------
# Main chat loop
# ----------------------------
MAX_TURNS = 20  # short-term window

def main() -> None:
    user_dir, sessions_dir = prompt_for_user()

    folder_name = os.path.basename(user_dir)
    parts = folder_name.split("-", 1)
    display_name = parts[1] if len(parts) == 2 else folder_name

    session_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    session_messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print(f"\nWelcome, {display_name}!")
    print("\nHow can I help you?\n")
    print("(Type 'exit' to end this session.)\n")

    while True:
        user_message = input("You: ")

        if user_message.strip().lower() == "exit":
            print("Goodbye!")
            save_session_and_summary(user_dir, sessions_dir, session_id, session_messages)
            break

        if not user_message.strip():
            ai_reply = random.choice(empty_replies)
            print(f"H: {ai_reply}\n")
            continue

        # --- Update messages ---
        user_item = {"role": "user", "content": user_message}
        messages.append(user_item)
        session_messages.append(user_item)

        # Short-term context
        system_msg = messages[0]
        dialog_body = [m for m in messages[1:] if m["role"] in {"user", "assistant"}]
        dialog_body = dialog_body[-MAX_TURNS:]

        # Long-term background memory
        memory_text = build_memory_background(user_dir, sessions_dir, user_message)
        if memory_text:
            memory_msg = {"role": "system", "content": memory_text}
            call_messages = [system_msg, memory_msg] + dialog_body
        else:
            call_messages = [system_msg] + dialog_body

        try:
            response = ollama.chat(
                model=MODEL,
                messages=call_messages,
                options={"temperature": 0.8, "top_p": 0.9},
            )
            answer = response["message"]["content"]
            print(f"H: {answer}\n")

            assistant_item = {"role": "assistant", "content": answer}
            messages.append(assistant_item)
            session_messages.append(assistant_item)

        except Exception as e:
            print(f"[Error] {e}\n")

if __name__ == "__main__":
    main()
