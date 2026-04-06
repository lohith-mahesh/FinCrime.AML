from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class ViolationCategory(str, Enum):
    STRUCTURING = "STRUCTURING"
    LAYERING = "LAYERING"
    SANCTIONS_MATCH = "SANCTIONS_MATCH"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NONE = "NONE"

class AMLAction(BaseModel):
    command: str
    account_id: Optional[str] = None
    search_name: Optional[str] = None
    violation_category: ViolationCategory = Field(default=ViolationCategory.NONE)
    complicit_account_ids: List[str] = Field(default_factory=list)
    verified_dob: Optional[str] = Field(default=None, description="Extracted DOB from account query (YYYY-MM-DD) if applicable.")
    rationale: Optional[str] = Field(default="No rationale provided")
    page: int = Field(default=1)

class AMLObservation(BaseModel):
    alert_id: str
    alert_trigger: str
    command_status: str
    database_response: str
    documented_evidence: List[str]
    reward: float
    done: bool

class AMLReward(BaseModel):
    reward: float
    info: Optional[dict] = {}