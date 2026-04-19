from fastapi import FastAPI
from pydantic import BaseModel
from backend.session import Session, new_session
from backend.coach import CoachSession
from backend.tts import BrowserTTSProvider
from backend.stt import WhisperSTT
from backend.ai.base import AbstractAIProvider


# In-memory session store: keyed by session_id
sessions: dict[str, Session] = {}

# Initialize concrete providers (Phase 0 stubs)
tts_provider = BrowserTTSProvider()
stt_provider = WhisperSTT()

# Placeholder AI provider for now (will be replaced in Phase 2)
class StubAIProvider(AbstractAIProvider):
    def chat(self, session: Session, user_text: str) -> str:
        return "[Phase 0 stub — AI not yet connected]"

ai_provider = StubAIProvider()

app = FastAPI()


class TurnRequest(BaseModel):
    session_id: str
    user_text: str


class TurnResponse(BaseModel):
    session_id: str
    coach_text: str
    transcript_norm: str
    error: str | None = None


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/turn")
def post_turn(request: TurnRequest) -> TurnResponse:
    """Handle a conversation turn.

    Phase 0: Creates a new session if it doesn't exist, processes the turn,
    and returns the coach response.

    Args:
        request: JSON body with session_id and user_text.

    Returns:
        TurnResponse with session_id, coach_text, transcript_norm, and error.
    """
    session_id = request.session_id
    user_text = request.user_text

    # Get or create session
    if session_id not in sessions:
        sessions[session_id] = new_session(
            topic="general",
            level=3,
            ai_provider="claude",
            coaching_mode="on_demand",
        )

    session = sessions[session_id]

    # Handle the turn
    coach_session = CoachSession(session, ai_provider)
    coach_turn = coach_session.handle_turn(user_text)

    return TurnResponse(
        session_id=session_id,
        coach_text=coach_turn.coach_text,
        transcript_norm=user_text,
        error=None,
    )
