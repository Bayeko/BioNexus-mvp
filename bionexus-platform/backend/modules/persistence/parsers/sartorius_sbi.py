# STATUS: PROTOTYPE — validated on simulated frames only
# Requires field testing with real instrument before GxP production use

"""Parser Sartorius SBI (Sartorius Balance Interface).

Protocole serie standard des balances Sartorius.
Format de trame : '+    22.5100 g  '
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


# Regex trame SBI : +    22.5100 g
SBI_PATTERN = re.compile(
    r'^([+-])\s+([\d]+\.[\d]+)\s+(\w+)\s*$'
)


def parse(line: str) -> ParsedMeasurement | None:
    line = line.strip()
    if not line:
        return None

    match = SBI_PATTERN.match(line)
    if not match:
        return None

    sign = match.group(1)
    value = float(match.group(2))
    unit = match.group(3)

    if sign == '-':
        value = -value

    data_hash = hashlib.sha256(line.encode('utf-8')).hexdigest()

    return ParsedMeasurement(
        value=value,
        unit=unit,
        parameter="weight",
        raw=line,
        data_hash=data_hash,
        idempotency_key=str(uuid.uuid4()),
        source_timestamp=datetime.now(timezone.utc).isoformat(),
        stable=True,
    )
