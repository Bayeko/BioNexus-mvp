# STATUS: PROTOTYPE — validated on simulated frames only
# Requires field testing with real instrument before GxP production use

"""Parser Mettler Toledo SICS (Standard Interface Command Set).

Protocole serie standard des balances Mettler Toledo.
Format de trame : 'S S      22.5000 g\r\n'
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ParsedMeasurement:
    value: float
    unit: str
    parameter: str
    raw: str
    data_hash: str
    idempotency_key: str
    source_timestamp: str
    stable: bool


# Regex trame SICS : S S      22.5000 g
SICS_PATTERN = re.compile(
    r'^S\s+([SD?])\s+([-+]?\d+\.\d+)\s+(\w+)\s*$'
)


def parse(line: str) -> ParsedMeasurement | None:
    line = line.strip()
    if not line:
        return None

    match = SICS_PATTERN.match(line)
    if not match:
        return None

    status = match.group(1)
    value = float(match.group(2))
    unit = match.group(3)
    stable = (status == 'S')

    data_hash = hashlib.sha256(line.encode('utf-8')).hexdigest()

    return ParsedMeasurement(
        value=value,
        unit=unit,
        parameter="weight",
        raw=line,
        data_hash=data_hash,
        idempotency_key=str(uuid.uuid4()),
        source_timestamp=datetime.now(timezone.utc).isoformat(),
        stable=stable,
    )
