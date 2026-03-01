from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class NegotiationDecision:
    action: str  # "ACCEPT" | "PROPOSE" | "REJECT"
    proposal: Optional[Dict] = None
