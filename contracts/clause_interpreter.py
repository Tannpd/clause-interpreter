# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass


@allow_storage
@dataclass
class InterpretationRecord:
    policy_clause: str
    event_description: str
    verdict: str  # APPLIES | DOES_NOT_APPLY | AMBIGUOUS
    confidence: bigint
    reasoning: str


def _normalize_verdict(verdict: str) -> str:
    v = str(verdict or "").strip().upper()
    if "DOES_NOT_APPLY" in v or "DOES NOT APPLY" in v or "NOT_APPLY" in v or "NOT APPLY" in v:
        return "DOES_NOT_APPLY"
    if "APPLIES" in v or "APPLY" in v:
        return "APPLIES"
    if "AMBIGUOUS" in v or "UNCERTAIN" in v or "AMBIG" in v:
        return "AMBIGUOUS"
    return "AMBIGUOUS"


def _normalize_confidence(conf_val: typing.Any) -> int:
    try:
        c = int(conf_val)
    except Exception:
        c = 0
    return max(0, min(100, c))


class Contract(gl.Contract):
    records: TreeMap[str, InterpretationRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.write
    def interpret_clause(self, policy_clause: str, event_description: str) -> None:
        if not policy_clause or not policy_clause.strip():
            raise gl.vm.UserError("policy_clause must not be empty")
        if not event_description or not event_description.strip():
            raise gl.vm.UserError("event_description must not be empty")

        clause_clean = policy_clause.strip()
        event_clean = event_description.strip()

        def leader_fn() -> str:
            prompt = f"""You are an impartial administrative arbiter.
Evaluate if the described real-world event triggers or violates the subjective policy clause, or if the situation is ambiguous.

POLICY CLAUSE:
---
{clause_clean}
---

REAL-WORLD EVENT:
---
{event_clean}
---

Rules for interpretation:
- Assign "APPLIES" if the real-world event clearly falls under the scope, triggers, or violates the subjective policy clause.
- Assign "DOES_NOT_APPLY" if the real-world event clearly does not fall under the scope, trigger, or violate the policy clause.
- Assign "AMBIGUOUS" if the interaction between the event and the clause is borderline, uncertain, or could reasonably be argued either way.
- Assign a confidence score from 0 to 100 representing how confident you are in this administrative decision.
- Provide a brief reasoning (maximum 200 characters) explaining the findings.

Respond ONLY with a valid JSON object matching the following structure:
{{
  "verdict": "APPLIES" | "DOES_NOT_APPLY" | "AMBIGUOUS",
  "confidence": <integer 0-100>,
  "reasoning": "explanation string"
}}"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}

            verdict = _normalize_verdict(res.get("verdict", "AMBIGUOUS"))
            confidence = _normalize_confidence(res.get("confidence", 0))
            reasoning = str(res.get("reasoning", "")).strip()[:200]
            if not reasoning:
                reasoning = "No reasoning provided."

            return json.dumps({
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning
            }, sort_keys=True)

        def validator_fn(leader_res: typing.Any) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_res.calldata)
            except Exception:
                return False

            leader_verdict = _normalize_verdict(leader_data.get("verdict"))
            leader_confidence = _normalize_confidence(leader_data.get("confidence"))

            try:
                mine_json = leader_fn()
                mine_data = json.loads(mine_json)
            except Exception:
                return False

            mine_verdict = _normalize_verdict(mine_data.get("verdict"))
            mine_confidence = _normalize_confidence(mine_data.get("confidence"))

            if leader_verdict != mine_verdict:
                return False

            if abs(leader_confidence - mine_confidence) > 15:
                return False

            return True

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        payload = json.loads(raw_result)

        rid = str(self.next_id)
        self.records[rid] = InterpretationRecord(
            policy_clause=clause_clean,
            event_description=event_clean,
            verdict=_normalize_verdict(payload.get("verdict")),
            confidence=bigint(_normalize_confidence(payload.get("confidence"))),
            reasoning=str(payload.get("reasoning")).strip()[:200]
        )
        self.next_id = self.next_id + bigint(1)

    @gl.public.view
    def get_record(self, record_id: str) -> str:
        if record_id not in self.records:
            raise gl.vm.UserError("Interpretation record not found")
        
        record = self.records[record_id]
        return json.dumps({
            "id": record_id,
            "policy_clause": record.policy_clause,
            "event_description": record.event_description,
            "verdict": record.verdict,
            "confidence": int(record.confidence),
            "reasoning": record.reasoning
        })

    @gl.public.view
    def get_total_records(self) -> int:
        return int(self.next_id)
