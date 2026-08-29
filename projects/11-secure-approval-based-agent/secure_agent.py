from __future__ import annotations
import time
from approvals import ApprovalManager
from audit import AuditLog
from authorization import Authorizer
from executor import SandboxedExecutor
from guardrails import inspect_user_input
from models import Action, AgentResponse, ApprovalToken, Decision, Principal
from planner import Planner
from policy import PolicyEngine
from rate_limit import RateLimiter

class SecureApprovalAgent:
    def __init__(self, *, policy: PolicyEngine | None = None, clock=time.time, approval_signing_key: bytes | None = None) -> None:
        self.policy = policy or PolicyEngine()
        self.clock = clock
        self.planner = Planner()
        self.authorizer = Authorizer(self.policy.data)
        self.audit = AuditLog(clock=clock)
        limits = self.policy.limits
        self.rate_limiter = RateLimiter(
            int(limits["max_requests_per_window"]),
            int(limits["rate_window_seconds"]),
        )
        self.approvals = ApprovalManager(
            int(limits["approval_ttl_seconds"]),
            signing_key=approval_signing_key, clock=clock,
        )
        self.executor = SandboxedExecutor(self.policy)

    def request(self, principal: Principal, text: str) -> AgentResponse:
        now = float(self.clock())
        rate_ok, count = self.rate_limiter.allow(principal.id, now)
        if not rate_ok:
            self.audit.append(principal, "rate_limit", action_type=None, outcome="blocked", details={"count": count})
            return AgentResponse("blocked", "Rate limit exceeded.")

        guard = inspect_user_input(text, max_chars=int(self.policy.limits["max_request_chars"]))
        if not guard.allowed:
            self.audit.append(principal, "input_guardrail", action_type=None, outcome="blocked",
                              details={"reason": guard.reason, "signals": list(guard.signals)})
            return AgentResponse("blocked", guard.reason)

        actions = self.planner.plan(text)
        if len(actions) > int(self.policy.limits["max_actions_per_request"]):
            self.audit.append(principal, "planning", action_type=None, outcome="blocked",
                              details={"reason": "too_many_actions"})
            return AgentResponse("blocked", "Too many actions were planned.")
        if len(actions) != 1:
            return AgentResponse("blocked", "This demo requires exactly one explicit action per request.")

        action = actions[0]
        decision = self.policy.classify(action)
        self.audit.append(principal, "policy", action_type=action.type, outcome=decision.decision.value,
                          details={"risk": decision.risk.value, "reason": decision.reason})

        if decision.decision == Decision.DENY:
            return AgentResponse("blocked", decision.reason, action=action)

        authorized, auth_reason = self.authorizer.is_authorized(principal, decision.permission)
        self.audit.append(principal, "authorization", action_type=action.type,
                          outcome="allowed" if authorized else "blocked",
                          details={"permission": decision.permission, "reason": auth_reason})
        if not authorized:
            return AgentResponse("blocked", auth_reason, action=action)

        if decision.decision == Decision.REQUIRE_APPROVAL:
            approval = self.approvals.create_request(principal, action)
            self.audit.append(principal, "approval_requested", action_type=action.type, outcome="pending",
                              details={"request_id": approval.id, "expires_at": approval.expires_at})
            return AgentResponse("approval_required", "Human approval is required before execution.",
                                 action=action, approval_request=approval)

        result = self.executor.execute(action)
        self.audit.append(principal, "execution", action_type=action.type, outcome=result.status,
                          details={"message": result.message})
        return AgentResponse(result.status, result.message, action=action, result=result)

    def approve(self, request_id: str, *, approver_id: str) -> ApprovalToken:
        token = self.approvals.approve(request_id, approver_id=approver_id)
        request = self.approvals.get(request_id)
        principal = Principal(request.principal_id if request else "unknown", "approval")
        self.audit.append(principal, "approval_granted", action_type=request.action_type if request else None,
                          outcome="approved", details={"request_id": request_id, "approver_id": approver_id})
        return token

    def reject(self, request_id: str, *, approver_id: str):
        request = self.approvals.reject(request_id)
        principal = Principal(request.principal_id, "approval")
        self.audit.append(principal, "approval_rejected", action_type=request.action_type, outcome="rejected",
                          details={"request_id": request_id, "approver_id": approver_id})
        return request

    def execute_approved(self, principal: Principal, action: Action, token: ApprovalToken) -> AgentResponse:
        decision = self.policy.classify(action)
        if decision.decision != Decision.REQUIRE_APPROVAL:
            self.audit.append(principal, "approved_execution", action_type=action.type, outcome="blocked",
                              details={"reason": "approval_not_applicable"})
            return AgentResponse("blocked", "Approval token is not applicable to this action.", action=action)

        authorized, auth_reason = self.authorizer.is_authorized(principal, decision.permission)
        if not authorized:
            self.audit.append(principal, "approved_execution", action_type=action.type, outcome="blocked",
                              details={"reason": auth_reason})
            return AgentResponse("blocked", auth_reason, action=action)

        valid, reason = self.approvals.validate(token, principal=principal, action=action)
        if not valid:
            self.audit.append(principal, "approved_execution", action_type=action.type, outcome="blocked",
                              details={"reason": reason})
            return AgentResponse("blocked", reason, action=action)

        result = self.executor.execute(action)
        if result.status in {"executed", "idempotent_replay"}:
            self.approvals.consume(token)

        self.audit.append(principal, "approved_execution", action_type=action.type, outcome=result.status,
                          details={"request_id": token.request_id, "message": result.message})
        return AgentResponse(result.status, result.message, action=action, result=result)
