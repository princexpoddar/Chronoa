"""
CHRONOS Cryptographic Audit Trail.

Implements the SHA-256 hash-chaining logic for the audit log, guaranteeing
that analyst decisions (Stage 10c) are tamper-evident, satisfying R6.4.
"""

import hashlib
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class AuditRecord:
    record_id: int
    candidate_id: str
    analyst_id: str
    decision: str
    rationale: str
    timestamp: str
    prev_hash: str
    current_hash: str = ""

class AuditLogger:
    def __init__(self):
        # In production, this reads/writes to Postgres `audit_trail` table
        self.chain: list[AuditRecord] = []
        self._genesis_hash = "0" * 64

    def _compute_hash(self, record: dict, prev_hash: str) -> str:
        """Compute SHA-256 over the canonical JSON of the record and previous hash."""
        # Remove current_hash if it exists in the dict
        record_copy = record.copy()
        record_copy.pop("current_hash", None)
        record_copy.pop("record_id", None)
        
        canonical_str = json.dumps(record_copy, sort_keys=True)
        payload = f"{canonical_str}|{prev_hash}".encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    def log_decision(self, candidate_id: str, analyst_id: str, decision: str, rationale: str) -> AuditRecord:
        """Append a new decision to the tamper-evident log."""
        prev_hash = self.chain[-1].current_hash if self.chain else self._genesis_hash
        new_id = len(self.chain) + 1
        
        record = AuditRecord(
            record_id=new_id,
            candidate_id=candidate_id,
            analyst_id=analyst_id,
            decision=decision,
            rationale=rationale,
            timestamp=datetime.utcnow().isoformat() + "Z",
            prev_hash=prev_hash
        )
        
        record.current_hash = self._compute_hash(asdict(record), prev_hash)
        self.chain.append(record)
        return record

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit chain."""
        if not self.chain:
            return True
            
        prev = self._genesis_hash
        for record in self.chain:
            if record.prev_hash != prev:
                return False
            computed = self._compute_hash(asdict(record), prev)
            if computed != record.current_hash:
                return False
            prev = record.current_hash
        return True
