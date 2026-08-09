# HollyAI

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10-3776AB?logo=python&logoColor=white)

A local, memory-aware AI assistant ("H") built in Python on top of [Ollama](https://ollama.com) and Llama 3. Runs entirely in your terminal, on your own machine — no data leaves your computer.

## Features

- **Multi-user** — each person gets a unique 5-digit ID and their own profile, so the same assistant can talk to different people (family, friends) while keeping their context separate.
- **Persistent memory** — every session is saved to disk, and after each session the assistant summarizes it into short keyword/topic tags stored in a monthly file.
- **Long-term recall** — on future sessions, H pulls in relevant past summaries and the most relevant matching past conversation for whatever you're currently talking about, so it stays consistent with your life, projects, and preferences without you having to repeat yourself.
- **Short-term context window** — the last 20 turns of the live conversation are kept in full for natural back-and-forth.

## How it works

1. Run the script, identify yourself (new user or existing 5-digit ID).
2. Chat normally in the terminal — type `exit` to end the session.
3. On exit, the session is saved and an LLM call extracts keyword-style memory tags from it (topics, tasks, people, plans, emotions) into that month's summary file.
4. Next time you chat, H searches past summaries for anything relevant to what you're currently saying and quietly folds it into its context before replying — so it can remember things across sessions without a full transcript being replayed every time.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running, with the model pulled:
  ```bash
  ollama pull llama3
  ```
  (the `ollama` Python package is installed automatically on first run if it's missing)

## Usage

```bash
python "text FINAL.py"
```

## Data & privacy

All conversation data — profiles, per-session transcripts, and monthly summaries — is written locally under `users/`, which is git-ignored and never leaves your machine. Nothing is sent anywhere except to your local Ollama instance.

## License

MIT — see [LICENSE](LICENSE).
