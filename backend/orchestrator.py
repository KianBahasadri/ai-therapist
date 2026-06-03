from __future__ import annotations

import asyncio

from backend.llm import LLMClient


ASSESSMENT_PROMPTS = {
    "emotional_state": "Assess the user's current emotional state from the latest message. Be concise and do not diagnose.",
    "risk": "Assess whether the latest message suggests immediate danger, self-harm, harm to others, abuse, coercion, or inability to stay safe. Be concise.",
    "withheld_context": "Assess whether the user may be omitting context that would materially affect a helpful response. Be concise.",
    "therapeutic_direction": "Suggest the most appropriate conversational direction for a supportive assistant. Be concise and avoid clinical overreach.",
}


class ChatOrchestrator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def respond(self, messages: list[dict], notes: str, latest_user_message: str) -> dict[str, str | dict[str, str]]:
        transcript = self._format_transcript(messages)
        assessment_input = f"Running notes:\n{notes or '(none)'}\n\nConversation:\n{transcript}\n\nLatest user message:\n{latest_user_message}"

        assessment_requests = [
            {
                "kind": kind,
                "system": prompt,
                "user": assessment_input,
                "temperature": 0.1,
            }
            for kind, prompt in ASSESSMENT_PROMPTS.items()
        ]
        assessment_items = await asyncio.gather(
            *[
                self.llm.complete(
                    system=request["system"],
                    user=request["user"],
                    temperature=request["temperature"],
                )
                for request in assessment_requests
            ]
        )
        assessments = dict(zip(ASSESSMENT_PROMPTS.keys(), assessment_items, strict=True))
        calls = [
            {
                "kind": f"assessment:{request['kind']}",
                "request": {
                    "system": request["system"],
                    "user": request["user"],
                    "temperature": request["temperature"],
                },
                "response": response,
            }
            for request, response in zip(assessment_requests, assessment_items, strict=True)
        ]

        notes_system = (
                "Update running notes for continuity. Keep stable user preferences, important context, "
                "and safety-relevant details. Do not include unsupported claims."
        )
        notes_user = f"Existing notes:\n{notes or '(none)'}\n\nConversation:\n{transcript}\n\nAssessments:\n{assessments}"
        notes_update = await self.llm.complete(
            system=notes_system,
            user=notes_user,
            temperature=0.1,
        )
        calls.append(
            {
                "kind": "notes_update",
                "request": {"system": notes_system, "user": notes_user, "temperature": 0.1},
                "response": notes_update,
            }
        )

        reply_system = (
                "You are a supportive conversational assistant for a supervised research prototype. "
                "Be warm, direct, and practical. Do not claim to be a licensed therapist. "
                "If there is immediate danger or self-harm risk, prioritize emergency support and encourage contacting local emergency services or a trusted person."
        )
        reply_user = (
                f"Running notes:\n{notes_update}\n\n"
                f"Internal assessments:\n{assessments}\n\n"
                f"Conversation:\n{transcript}\n\n"
                "Write the next assistant response."
        )
        reply = await self.llm.complete(
            system=reply_system,
            user=reply_user,
            temperature=0.5,
        )
        calls.append(
            {
                "kind": "therapist_response",
                "request": {"system": reply_system, "user": reply_user, "temperature": 0.5},
                "response": reply,
            }
        )

        return {"reply": reply, "notes": notes_update, "assessments": assessments, "calls": calls}

    async def simulate_user_response(self, messages: list[dict], notes: str) -> str:
        transcript = self._format_transcript(messages)
        return await self.llm.complete(
            system=(
                "You simulate the next user message in a therapy research debug harness. "
                "Write only the user's next message in first person. Keep it realistic, concise, "
                "and emotionally specific. Do not roleplay the assistant. Do not introduce immediate "
                "danger, self-harm, harm to others, or abuse unless it is already clearly present in the conversation."
            ),
            user=(
                f"Running notes visible to the therapist:\n{notes or '(none)'}\n\n"
                f"Conversation so far:\n{transcript}\n\n"
                "Generate the next user response."
            ),
            temperature=0.7,
        )

    def _format_transcript(self, messages: list[dict]) -> str:
        if not messages:
            return "(empty)"
        return "\n".join(f"{message['role']}: {message['content']}" for message in messages[-24:])
