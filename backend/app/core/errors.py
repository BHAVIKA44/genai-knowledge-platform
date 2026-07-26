from dataclasses import dataclass


@dataclass
class DomainError(Exception):
    code: str
    message: str
    action: str | None = None
    status_code: int = 400


class InvalidStateTransitionError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "INVALID_STATE_TRANSITION",
            "This document cannot move to that processing stage.",
            status_code=409,
        )
