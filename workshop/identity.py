"""Single-presenter access gate; not a user directory or an IdP."""
from secrets import compare_digest

from fastapi import Header, HTTPException


def presenter_gate(token: str | None, hosted: bool):
    if hosted and not token:
        raise ValueError("Hosted mode requires WORKSHOP_TOKEN.")
    expected = f"Bearer {token}".encode() if token else None

    def require_presenter(authorization: str | None = Header(default=None)):
        if expected is not None and not compare_digest((authorization or "").encode(), expected):
            raise HTTPException(401, "Presenter token required.", {"WWW-Authenticate": "Bearer"})

    return require_presenter
