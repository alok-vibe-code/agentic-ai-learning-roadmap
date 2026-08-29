from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class RiskLevel(str, Enum):
    LOW = "LOW"
    SENSITIVE = "SENSITIVE"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN = "UNKNOWN"

class Decision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"

@dataclass(frozen=True)
class Principal:
    id: str
    role: str

@dataclass(frozen=True)
class Action:
    type: str
    parameters: dict[str, Any]
    idempotency_key: str | None = None

@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    risk: RiskLevel
    permission: str | None
    reason: str

@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str
    signals: tuple[str, ...] = ()

@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    principal_id: str
    action_type: str
    action_digest: str
    created_at: float
    expires_at: float
    status: str

@dataclass(frozen=True)
class ApprovalToken:
    request_id: str
    principal_id: str
    action_digest: str
    issued_at: float
    expires_at: float
    nonce: str
    signature: str

@dataclass(frozen=True)
class ExecutionResult:
    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    timestamp: float
    principal_id: str
    event_type: str
    action_type: str | None
    outcome: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str

@dataclass(frozen=True)
class AgentResponse:
    status: str
    message: str
    action: Action | None = None
    approval_request: ApprovalRequest | None = None
    result: ExecutionResult | None = None
