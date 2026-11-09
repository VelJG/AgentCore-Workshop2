"""Approval rules; executed by the application, never by the model."""
from pydantic import BaseModel, ConfigDict, Field

APPROVAL_TTL_SECONDS = 600
MAX_RECORDS = 1000


class TicketDraft(BaseModel):
    """Propose a synthetic support ticket; this does not create a ticket."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content: str = Field(min_length=1, max_length=500)


class DecisionConflict(Exception):
    pass


def next_status(status: str, *, approve: bool, expires_at: float, now: float) -> str:
    requested = "approved" if approve else "denied"
    if status == requested:
        return status
    if status != "pending":
        raise DecisionConflict("This approval has already been decided.")
    if expires_at <= now:
        raise DecisionConflict("This approval has expired. Request a new proposal.")
    return requested
