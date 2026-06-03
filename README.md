# ai-therapist

**mimic a licensed therapist** as closely as possible.
Obvious Disclaimer: if you have serious mental health issues you need to see a human expert.
This tool needs to be taken with a grain of salt.

## Run locally

```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
## High-Level Backend

1. The user chats with the AI through the web interface, following a normal conversational flow.
2. The backend holds the conversation history along with notes which are constantly being updated. Then multiple model calls are made with the same information but with a different focus. for example, one will assess the user's current emotional state of mind, another will assess if the user might be witholding any potential information, another may assess if the user is implying any dangerous behaviour, etc.)
3. Once the information is gathered, it is compiled and shown to an llm as ai generated suggestions along with the conversational history, and the llm will generate a response to send back to the user.
