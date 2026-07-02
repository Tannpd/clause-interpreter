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


class Contract(gl.Contract):
    records: TreeMap[str, InterpretationRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

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
