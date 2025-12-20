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
    "IMPORTANT: Your name is H, Sudheer's new AI assistant currently in development. "
    "Always introduce yourself ONLY as H. "
    "If the user asks who you are or your name, say, \"I'm H.\" "
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, "users")


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

    summary_path = os.path.join(user_dir, "summary.json")
    profile_path = os.path.join(user_dir, "profile.json")

    if not os.path.exists(summary_path):
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump([], f)

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
    summary_path = os.path.join(user_dir, "summary.json")

    os.makedirs(sessions_dir, exist_ok=True)

    if not os.path.exists(summary_path):
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    return sessions_dir, summary_path


def prompt_for_user():
    """
    Ask for user identity.
    NEW: user types 'new' -> chooses fresh 5-digit ID, then name + relationship.
    EXISTING: user types their existing 5-digit ID.
    """
    os.makedirs(USERS_DIR, exist_ok=True)

    print("Welcome to the world of Sudheer.")
    status = input(
        "If you're NEW, type 'new'.\n"
        "If you've used H before, type your 5-digit ID: "
    ).strip().lower()

    if status == "new":
        user_id = ask_for_new_5_digit_id()
        name = input("Enter your name? ").strip()
        relationship = input("Relationship with Sudheer? ").strip()
        user_dir = create_new_user_folder(user_id, name, relationship)
    else:
        # Treat input as existing ID
        user_id = status
        user_dir = find_user_folder_by_id(user_id)
        if user_dir is None:
            print("\nNo existing user found with that ID. Let's register you as new.")
            user_id = ask_for_new_5_digit_id()
            name = input("Enter your name? ").strip()
            relationship = input("Relationship with Sudheer? ").strip()
            user_dir = create_new_user_folder(user_id, name, relationship)

    sessions_dir, summary_path = ensure_existing_user_dirs(user_dir)
    return user_dir, sessions_dir, summary_path


# ----------------------------
# Summarization helpers
# ----------------------------
def build_session_summary_text(session_messages):
    """
    Use the LLM to generate keyword-style tags for the conversation.
    Example: "openai residency, github project, holly assistant".
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
        "From this conversation between a user and an AI assistant named H, "
        "extract 3–8 short topic keywords or tags. "
        "Focus on what the user wanted and the main subjects discussed. "
        "Respond ONLY with comma-separated keywords, no extra text.\n\n"
        f"{transcript}"
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate very short keyword tags for conversations. "
                    "Return only comma-separated keywords, no sentences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    text = response["message"]["content"]
    return text.strip() if isinstance(text, str) else "general"


def save_session_and_summary(
    sessions_dir,
    summary_path,
    session_id,
    session_messages,
):
    """
    Save full session and append a keyword-style summary entry.
    """
    # Use a file-safe ID for the file name
    file_friendly_id = session_id.replace(":", "-")
    session_path = os.path.join(sessions_dir, f"session_{file_friendly_id}.json")
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_messages, f, ensure_ascii=False, indent=2)

    # Generate summary using the LLM
    try:
        summary_text = build_session_summary_text(session_messages)
    except Exception as e:
        summary_text = f"[Summary generation failed inside code: {e}]"

    summary_item = {
        "session_id": session_id,
        "timestamp": session_id,
        "summary": summary_text,
    }

    # Append to summary.json
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
# Retrieval helpers (load past sessions)
# ----------------------------
def load_summaries(summary_path):
    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def find_best_session_for_query(summary_path, query: str):
    """
    Very simple keyword match: count how many query words appear in each summary.
    Returns the best summary dict or None.
    """
    summaries = load_summaries(summary_path)
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


def load_session_messages_by_id(sessions_dir, session_id: str):
    """
    Load messages from a previous session using its session_id
    (session_id uses colons; file name uses hyphens).
    """
    file_friendly_id = session_id.replace(":", "-")
    path = os.path.join(sessions_dir, f"session_{file_friendly_id}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


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
def main() -> None:
    user_dir, sessions_dir, summary_path = prompt_for_user()

    # ISO-like timestamp with colons (nice for JSON); use hyphens only in filenames
    session_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    session_messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    folder_name = os.path.basename(user_dir)
    # folder_name looks like "12345-Alice"
    parts = folder_name.split("-", 1)
    display_name = parts[1] if len(parts) == 2 else folder_name

    print(f"\nWelcome, {display_name}!")
    print("\nHow can I help you?\n")
    print("(Note: Type 'exit' to end this session.)\n")

    while True:
        user_message = input("You: ")

        if user_message.strip().lower() == "exit":
            print("Goodbye!")
            save_session_and_summary(sessions_dir, summary_path, session_id, session_messages)
            break

        if not user_message.strip():
            ai_reply = random.choice(empty_replies)
            print(f"H: {ai_reply}\n")
            continue

        # -------- Retrieval: try to load relevant past conversation --------
        past = find_best_session_for_query(summary_path, user_message)
        if past is not None:
            past_session_id = past.get("session_id")
            past_messages = load_session_messages_by_id(sessions_dir, past_session_id)

            trimmed_past = [
                m for m in past_messages
                if isinstance(m, dict) and m.get("role") in {"user", "assistant"}
            ][-20:]  # last 20 turns

            bridge = {
                "role": "system",
                "content": (
                    "The following is a previous conversation with this same user "
                    "about a related topic. Use it as background memory, but still "
                    "answer the user's new question directly."
                ),
            }

            messages.extend([bridge] + trimmed_past)
            session_messages.extend([bridge] + trimmed_past)

        # -------- Current turn --------
        user_item = {"role": "user", "content": user_message}
        messages.append(user_item)
        session_messages.append(user_item)

        try:
            response = ollama.chat(
                model=MODEL,
                messages=messages,
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
