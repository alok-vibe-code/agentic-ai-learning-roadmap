from __future__ import annotations
import hashlib, hmac, json, secrets, time
from models import Action, ApprovalRequest, ApprovalToken, Principal

def canonical_action(action: Action) -> str:
    return json.dumps(
        {"type": action.type, "parameters": action.parameters, "idempotency_key": action.idempotency_key},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )

def action_digest(action: Action) -> str:
    return hashlib.sha256(canonical_action(action).encode("utf-8")).hexdigest()

class ApprovalManager:
    def __init__(self, ttl_seconds: int, *, signing_key: bytes | None = None, clock=time.time) -> None:
        if ttl_seconds < 1:
            raise ValueError("Approval TTL must be positive.")
        self.ttl_seconds = ttl_seconds
        self.signing_key = signing_key or secrets.token_bytes(32)
        self.clock = clock
        self._requests: dict[str, ApprovalRequest] = {}
        self._used_nonces: set[str] = set()
        self._counter = 0

    def create_request(self, principal: Principal, action: Action) -> ApprovalRequest:
        self._counter += 1
        now = float(self.clock())
        request = ApprovalRequest(
            id=f"apr-{self._counter:04d}",
            principal_id=principal.id,
            action_type=action.type,
            action_digest=action_digest(action),
            created_at=now,
            expires_at=now + self.ttl_seconds,
            status="pending",
        )
        self._requests[request.id] = request
        return request

    def approve(self, request_id: str, *, approver_id: str) -> ApprovalToken:
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError("Unknown approval request.")
        now = float(self.clock())
        if now > request.expires_at:
            raise ValueError("Approval request has expired.")
        if request.status != "pending":
            raise ValueError("Approval request is not pending.")
        nonce = secrets.token_hex(8)
        payload = self._payload(
            request.id, request.principal_id, request.action_digest,
            now, request.expires_at, nonce, approver_id
        )
        signature = hmac.new(
            self.signing_key, payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._requests[request_id] = ApprovalRequest(**{**request.__dict__, "status": "approved"})
        return ApprovalToken(
            request_id=request.id,
            principal_id=request.principal_id,
            action_digest=request.action_digest,
            issued_at=now,
            expires_at=request.expires_at,
            nonce=nonce,
            signature=f"{approver_id}:{signature}",
        )

    def reject(self, request_id: str) -> ApprovalRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise ValueError("Unknown approval request.")
        if request.status != "pending":
            raise ValueError("Approval request is not pending.")
        rejected = ApprovalRequest(**{**request.__dict__, "status": "rejected"})
        self._requests[request_id] = rejected
        return rejected

    def validate(self, token: ApprovalToken, *, principal: Principal, action: Action) -> tuple[bool, str]:
        now = float(self.clock())
        request = self._requests.get(token.request_id)
        if request is None:
            return False, "Approval request does not exist."
        if request.status != "approved":
            return False, "Approval request is not approved."
        if now > token.expires_at or now > request.expires_at:
            return False, "Approval has expired."
        if token.nonce in self._used_nonces:
            return False, "Approval token has already been used."
        if token.principal_id != principal.id:
            return False, "Approval token belongs to another principal."
        digest = action_digest(action)
        if digest != token.action_digest or digest != request.action_digest:
            return False, "Action changed after approval."
        try:
            approver_id, supplied = token.signature.split(":", 1)
        except ValueError:
            return False, "Malformed approval signature."
        payload = self._payload(
            token.request_id, token.principal_id, token.action_digest,
            token.issued_at, token.expires_at, token.nonce, approver_id
        )
        expected = hmac.new(
            self.signing_key, payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            return False, "Approval signature is invalid."
        return True, "Approval token is valid."

    def consume(self, token: ApprovalToken) -> None:
        if token.nonce in self._used_nonces:
            raise ValueError("Approval token already consumed.")
        self._used_nonces.add(token.nonce)

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    @staticmethod
    def _payload(request_id, principal_id, action_digest_value, issued_at, expires_at, nonce, approver_id) -> str:
        return "|".join([
            request_id, principal_id, action_digest_value,
            str(issued_at), str(expires_at), nonce, approver_id
        ])
