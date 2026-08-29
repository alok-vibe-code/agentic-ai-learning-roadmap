from __future__ import annotations
import re
from models import Action

def _clean(value: str) -> str:
    return " ".join(value.strip().split())

class Planner:
    def plan(self, request: str) -> list[Action]:
        text = _clean(request)
        lower = text.casefold()

        if lower.startswith("read secret"):
            return [Action("read_secret", {"name": text[11:].strip()})]

        if lower.startswith("execute shell "):
            return [Action("execute_shell", {"command": text[14:]})]

        if lower.startswith("search "):
            return [Action("search", {"query": text[7:]})]

        if lower.startswith("read "):
            return [Action("read_resource", {"resource": text[5:]})]

        if lower.startswith("calculate "):
            return [Action("calculate", {"expression": text[10:]})]

        if lower.startswith("send email "):
            match = re.fullmatch(
                r"send email to (\S+) subject (.+?) body (.+)",
                text, flags=re.IGNORECASE
            )
            if not match:
                return [Action("unknown", {"raw": text})]
            return [Action("send_email", {
                "to": match.group(1),
                "subject": match.group(2),
                "body": match.group(3),
            })]

        if lower.startswith("publish "):
            return [Action("publish_content", {"content": text[8:]})]

        if lower.startswith("delete file "):
            return [Action("delete_file", {"path": text[12:]})]

        if lower.startswith("modify record "):
            match = re.fullmatch(
                r"modify record ([A-Za-z0-9_-]+) set ([A-Za-z0-9_-]+)=(.+)",
                text, flags=re.IGNORECASE
            )
            if not match:
                return [Action("unknown", {"raw": text})]
            return [Action("modify_external_record", {
                "record_id": match.group(1),
                "field": match.group(2),
                "value": match.group(3),
            })]

        if lower.startswith("transfer "):
            match = re.fullmatch(
                r"transfer ([0-9]+(?:\.[0-9]+)?) to ([A-Za-z0-9_-]+)",
                text, flags=re.IGNORECASE
            )
            if not match:
                return [Action("unknown", {"raw": text})]
            return [Action("financial_transfer", {
                "amount": float(match.group(1)),
                "destination": match.group(2),
            })]

        return [Action("unknown", {"raw": text})]
