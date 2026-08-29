from __future__ import annotations
import json
from pathlib import Path
from models import Action, Decision, PolicyDecision, RiskLevel

DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "data" / "policy.json"

class PolicyEngine:
    def __init__(self, path: str | Path | None = None) -> None:
        policy_path = Path(path) if path else DEFAULT_POLICY_PATH
        self.data = json.loads(policy_path.read_text(encoding="utf-8"))
        if not isinstance(self.data.get("actions"), dict):
            raise ValueError("Policy requires an actions mapping.")
        if not isinstance(self.data.get("roles"), dict):
            raise ValueError("Policy requires a roles mapping.")

    @property
    def limits(self) -> dict:
        return dict(self.data.get("limits", {}))

    @property
    def allowlisted_resources(self) -> set[str]:
        return set(self.data.get("allowlisted_resources", []))

    def classify(self, action: Action) -> PolicyDecision:
        config = self.data["actions"].get(action.type)
        if config is None:
            return PolicyDecision(Decision.DENY, RiskLevel.UNKNOWN, None, "Unknown actions fail closed.")
        try:
            risk = RiskLevel(config["risk"])
        except Exception:
            return PolicyDecision(Decision.DENY, RiskLevel.UNKNOWN, None, "Malformed action policy fails closed.")
        permission = config.get("permission")
        if risk == RiskLevel.FORBIDDEN:
            return PolicyDecision(Decision.DENY, risk, permission, "Action is explicitly forbidden.")
        if risk == RiskLevel.SENSITIVE:
            return PolicyDecision(Decision.REQUIRE_APPROVAL, risk, permission, "Sensitive action requires human approval.")
        if risk == RiskLevel.LOW:
            return PolicyDecision(Decision.ALLOW, risk, permission, "Low-risk action may execute after authorization.")
        return PolicyDecision(Decision.DENY, RiskLevel.UNKNOWN, permission, "Unrecognized risk level fails closed.")
