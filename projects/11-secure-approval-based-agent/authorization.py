from __future__ import annotations
from models import Principal

class Authorizer:
    def __init__(self, policy_data: dict) -> None:
        self.roles = policy_data.get("roles", {})

    def is_authorized(self, principal: Principal, permission: str | None) -> tuple[bool, str]:
        if permission is None:
            return False, "Action has no valid permission mapping."
        permissions = self.roles.get(principal.role)
        if permissions is None:
            return False, f"Unknown role: {principal.role}"
        if permission not in permissions:
            return False, f"Role {principal.role} lacks permission {permission}."
        return True, "Principal is authorized."
